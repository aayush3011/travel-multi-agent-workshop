import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet, RouterLink, RouterLinkActive, Router } from '@angular/router';
import { TravelApiService } from './services/travel-api.service';
import { User } from './models/travel.models';

@Component({
    selector: 'app-root',
    imports: [CommonModule, RouterOutlet, RouterLink, RouterLinkActive],
    templateUrl: './app.component.html',
    styleUrls: ['./app.component.css']
})
export class AppComponent implements OnInit {
  title = 'Cosmos Voyager';
  currentUser: User | null = null;
  
  screens = [
    { key: 'explore', label: 'Explore', route: '/explore' },
    { key: 'profile', label: 'Profile & Memories', route: '/profile' },
    { key: 'trips', label: 'My Trips', route: '/trips' }
  ];

  constructor(
    public router: Router,
    private travelApiService: TravelApiService
  ) {}

  ngOnInit(): void {
    // Subscribe to current user changes
    this.travelApiService.currentUser$.subscribe(user => {
      this.currentUser = user;
      
      // If no user and not on login page, redirect to login
      if (!user && this.router.url !== '/login') {
        this.router.navigate(['/login']);
      }
    });
  }

  logout(): void {
    this.travelApiService.logout();
    this.router.navigate(['/login']);
  }

  get isLoggedIn(): boolean {
    return this.currentUser !== null;
  }

  get isLoginPage(): boolean {
    return this.router.url === '/login';
  }
}
