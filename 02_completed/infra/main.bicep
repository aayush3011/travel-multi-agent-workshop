targetScope = 'subscription'

@minLength(1)
@maxLength(64)
@description('Name of the environment that can be used as part of naming resource convention')
param environmentName string

@minLength(1)
@description('Primary location for all resources')
param location string

@description('Id of the user or app to assign application roles')
param principalId string

@description('Id of the service principal to assign application roles (optional - if not provided, SP roles will be skipped)')
param servicePrincipalId string = ''

@description('Owner tag for resource tagging')
param owner string = 'defaultuser@example.com'

var tags = {
  'azd-env-name': environmentName
  'owner': owner
}

var abbrs = loadJsonContent('./abbreviations.json')
var resourceToken = toLower(uniqueString(subscription().id, environmentName, location))

resource rg 'Microsoft.Resources/resourceGroups@2022-09-01' = {
  name: 'rg-${environmentName}'
  location: location
  tags: tags
}

// Deploy Managed Identity
module managedIdentity './shared/managedidentity.bicep' = {
  name: 'managed-identity'
  params: {
    identityName: '${abbrs.managedIdentityUserAssignedIdentities}${resourceToken}'
    location: location
    tags: tags
  }
  scope: rg
}

// Deploy Azure Cosmos DB
module cosmos './shared/cosmosdb.bicep' = {
  name: 'cosmos'
  params: {
    name: '${abbrs.documentDBDatabaseAccounts}${resourceToken}'
    location: location
    tags: tags
    databaseName: 'TravelAssistant'
    sessionsContainerName: 'Sessions'
    messagesContainerName: 'Messages'
    summariesContainerName: 'Summaries'
    memoriesContainerName: 'Memories'
    apiEventsContainerName: 'ApiEvents'
    placesContainerName: 'Places'
    tripsContainerName: 'Trips'
    usersContainerName: 'Users'
    debugLogsContainerName: 'Debug'
    checkpointsContainerName: 'Checkpoints'
  }
  scope: rg
}

// Deploy OpenAI
module openAi './shared/openai.bicep' = {
  name: 'openai-account'
  params: {
    name: '${abbrs.openAiAccounts}${resourceToken}'
    location: 'westus'
    tags: tags
    sku: 'S0'
  }
  scope: rg
}

//Deploy OpenAI Deployments
var deployments = [
  {
    name: 'gpt-4.1-mini'
    skuCapacity: 30
	skuName: 'GlobalStandard'
    modelName: 'gpt-4.1-mini'
    modelVersion: '2025-04-14'
  }
  {
    name: 'text-embedding-3-small'
    skuCapacity: 5
	skuName: 'GlobalStandard'
    modelName: 'text-embedding-3-small'
    modelVersion: '1'
  }
]

@batchSize(1)
module openAiModelDeployments './shared/modeldeployment.bicep' = [
  for (deployment, _) in deployments: {
    name: 'openai-model-deployment-${deployment.name}'
    params: {
      name: deployment.name
      parentAccountName: openAi.outputs.name
      skuName: deployment.skuName
      skuCapacity: deployment.skuCapacity
      modelName: deployment.modelName
      modelVersion: deployment.modelVersion
      modelFormat: 'OpenAI'
    }
	scope: rg
  }
]

//Assign Roles to Managed Identities
module AssignRoles './shared/assignroles.bicep' = {
  name: 'AssignRoles'
  params: {
    cosmosDbAccountName: cosmos.outputs.name
    openAIName: openAi.outputs.name
    identityName: managedIdentity.outputs.name
	  userPrincipalId: !empty(principalId) ? principalId : null
	servicePrincipalId: !empty(servicePrincipalId) ? servicePrincipalId : ''
  }
  scope: rg
}

// Deploy Log Analytics Workspace
module logAnalytics './shared/loganalytics.bicep' = {
  name: 'log-analytics'
  params: {
    name: '${abbrs.operationalInsightsWorkspaces}${resourceToken}'
    location: location
    tags: tags
  }
  scope: rg
}

// Deploy Container Registry
module containerRegistry './shared/containerregistry.bicep' = {
  name: 'container-registry'
  params: {
    name: '${abbrs.containerRegistryRegistries}${resourceToken}'
    location: location
    tags: tags
    identityPrincipalId: managedIdentity.outputs.principalId
  }
  scope: rg
}

// Deploy Container Apps Environment
module containerAppsEnvironment './shared/containerappenvironment.bicep' = {
  name: 'container-apps-environment'
  params: {
    name: '${abbrs.appManagedEnvironments}${resourceToken}'
    location: location
    tags: tags
    logAnalyticsWorkspaceName: logAnalytics.outputs.name
  }
  scope: rg
}

// Deploy MCP Server Container App (internal only - called by FastAPI)
module mcpServerApp './shared/containerapp.bicep' = {
  name: 'mcp-server-app'
  params: {
    name: '${abbrs.appContainerApps}mcp-${resourceToken}'
    location: location
    tags: union(tags, { 'azd-service-name': 'mcp-server' })
    environmentId: containerAppsEnvironment.outputs.id
    containerRegistryLoginServer: containerRegistry.outputs.loginServer
    targetPort: 8080
    identityId: managedIdentity.outputs.id
    external: false
    minReplicas: 1
    maxReplicas: 3
    cpu: '1'
    memory: '2Gi'
    env: [
      { name: 'COSMOSDB_ENDPOINT', value: cosmos.outputs.endpoint }
      { name: 'COSMOS_DB_DATABASE_NAME', value: 'TravelAssistant' }
      { name: 'AZURE_OPENAI_ENDPOINT', value: openAi.outputs.endpoint }
      { name: 'AZURE_OPENAI_EMBEDDING_DEPLOYMENT', value: 'text-embedding-3-small' }
      { name: 'AZURE_OPENAI_DEPLOYMENT', value: 'gpt-4.1-mini' }
      { name: 'AZURE_OPENAI_API_VERSION', value: '2024-12-01-preview' }
      { name: 'AZURE_CLIENT_ID', value: managedIdentity.outputs.clientId }
      { name: 'PORT', value: '8080' }
    ]
  }
  scope: rg
}

// Deploy FastAPI Backend Container App (internal only - called by frontend)
module apiApp './shared/containerapp.bicep' = {
  name: 'api-app'
  params: {
    name: '${abbrs.appContainerApps}api-${resourceToken}'
    location: location
    tags: union(tags, { 'azd-service-name': 'api' })
    environmentId: containerAppsEnvironment.outputs.id
    containerRegistryLoginServer: containerRegistry.outputs.loginServer
    targetPort: 8000
    identityId: managedIdentity.outputs.id
    external: false
    minReplicas: 1
    maxReplicas: 3
    cpu: '1'
    memory: '2Gi'
    env: [
      { name: 'COSMOSDB_ENDPOINT', value: cosmos.outputs.endpoint }
      { name: 'COSMOS_DB_DATABASE_NAME', value: 'TravelAssistant' }
      { name: 'AZURE_OPENAI_ENDPOINT', value: openAi.outputs.endpoint }
      { name: 'AZURE_OPENAI_EMBEDDING_DEPLOYMENT', value: 'text-embedding-3-small' }
      { name: 'AZURE_OPENAI_DEPLOYMENT', value: 'gpt-4.1-mini' }
      { name: 'AZURE_OPENAI_API_VERSION', value: '2024-12-01-preview' }
      { name: 'AZURE_CLIENT_ID', value: managedIdentity.outputs.clientId }
      { name: 'MCP_SERVER_BASE_URL', value: 'http://${mcpServerApp.outputs.fqdn}' }
      { name: 'PORT', value: '8000' }
    ]
  }
  scope: rg
}

// Deploy Frontend Container App (external - public facing)
module frontendApp './shared/containerapp.bicep' = {
  name: 'frontend-app'
  params: {
    name: '${abbrs.appContainerApps}web-${resourceToken}'
    location: location
    tags: union(tags, { 'azd-service-name': 'frontend' })
    environmentId: containerAppsEnvironment.outputs.id
    containerRegistryLoginServer: containerRegistry.outputs.loginServer
    targetPort: 80
    identityId: managedIdentity.outputs.id
    external: true
    minReplicas: 1
    maxReplicas: 3
    cpu: '0.25'
    memory: '0.5Gi'
    env: [
      { name: 'API_BASE_URL', value: 'http://${apiApp.outputs.fqdn}' }
    ]
  }
  scope: rg
}


// Outputs
output RG_NAME string = 'rg-${environmentName}'
output COSMOSDB_ENDPOINT string = cosmos.outputs.endpoint
output AZURE_OPENAI_ENDPOINT string = openAi.outputs.endpoint
output AZURE_OPENAI_COMPLETIONSDEPLOYMENTID string = openAiModelDeployments[0].outputs.name
output AZURE_OPENAI_EMBEDDINGDEPLOYMENTID string = openAiModelDeployments[1].outputs.name
output AZURE_CONTAINER_REGISTRY_ENDPOINT string = containerRegistry.outputs.loginServer
output AZURE_CONTAINER_REGISTRY_NAME string = containerRegistry.outputs.name
output FRONTEND_URI string = frontendApp.outputs.uri
output API_URI string = apiApp.outputs.uri
output MCP_SERVER_URI string = mcpServerApp.outputs.uri
