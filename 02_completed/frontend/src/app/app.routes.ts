import { Routes } from '@angular/router';

export const routes: Routes = [
  { path: '', redirectTo: '/login', pathMatch: 'full' },
  { 
    path: 'login', 
    loadComponent: () => import('./components/login/login.component').then(m => m.LoginComponent)
  },
  { 
    path: 'home', 
    loadComponent: () => import('./components/home/home.component').then(m => m.HomeComponent)
  },
  { 
    path: 'explore', 
    loadComponent: () => import('./components/explore/explore.component').then(m => m.ExploreComponent)
  },
  { 
    path: 'profile', 
    loadComponent: () => import('./components/profile/profile.component').then(m => m.ProfileComponent)
  },
  { 
    path: 'trips', 
    loadComponent: () => import('./components/trips/trips.component').then(m => m.TripsComponent)
  }
];

