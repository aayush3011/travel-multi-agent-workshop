export interface Thread {
  id: string;
  threadId: string;
  tenantId: string;
  userId: string;
  title: string;
  activeAgent?: string;
  createdAt: string;
  lastMessageAt: string;
  messageCount?: number;
}

export interface Message {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp?: string;
  metadata?: {
    agent?: string;
    toolCalls?: string[];
  };
}

export interface Place {
  id: string;
  geoScopeId: string;
  type: 'hotel' | 'restaurant' | 'attraction';
  name: string;
  description: string;
  neighborhood?: string;
  rating?: number;
  priceTier?: 'budget' | 'moderate' | 'upscale' | 'luxury';
  tags?: string[];
  accessibility?: string[];
  hours?: { [key: string]: string };
  restaurantSpecific?: {
    cuisineTypes?: string[];
    dietaryOptions?: string[];
    seatingOptions?: string[];
  };
  hotelSpecific?: {
    amenities?: string[];
  };
  attractionSpecific?: {
    ticketRequired?: boolean;
    duration?: string;
  };
}

export interface Trip {
  id: string;
  tripId: string;
  tenantId: string;
  userId: string;
  destination: string;
  startDate: string;
  endDate: string;
  status: 'planning' | 'confirmed' | 'completed';
  days?: TripDay[];
  createdAt: string;
}

export interface TripDay {
  dayNumber: number;
  date: string;
  morning?: TripActivity;
  lunch?: TripActivity;
  afternoon?: TripActivity;
  dinner?: TripActivity;
  evening?: TripActivity;
  accommodation?: TripActivity;
}

export interface TripActivity {
  activity: string;
  time?: string;
  placeId?: string;
  place?: Place;
}

export interface Memory {
  id: string;
  memoryId: string;
  tenantId: string;
  userId: string;
  category: 'hotel' | 'dining' | 'activity' | 'trip';
  key: string;
  value: string;
  facet: string;
  memoryType: 'declarative' | 'procedural' | 'episodic';
  createdAt: string;
  ttl?: number;
}

export interface ChatCompletionResponse {
  threadId: string;
  messages: Message[];
  activeAgent?: string;
}

export interface PlaceSearchRequest {
  geoScope: string;
  placeTypes: string[];
  searchEmbedding: string;
  topK?: number;
  filters?: {
    type?: string;
    dietary?: string;
    priceTier?: string;
  };
}

export interface User {
  id: string;
  userId: string;
  tenantId: string;
  name: string;
  gender?: string;
  age?: number;
  phone?: string;
  address?: {
    street?: string;
    city?: string;
    state?: string;
    zip?: string;
    country?: string;
  };
  email?: string;
  createdAt: string;
}

export interface City {
  id: string;
  name: string;
  displayName: string;
}

export interface PlaceFilterRequest {
  city: string;
  types?: string[];
  priceTiers?: string[];
  dietary?: string[];
  accessibility?: string[];
}

