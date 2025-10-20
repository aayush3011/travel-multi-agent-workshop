import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet, RouterLink, RouterLinkActive, Router } from '@angular/router';

@Component({
    selector: 'app-root',
    imports: [CommonModule, RouterOutlet, RouterLink, RouterLinkActive],
    templateUrl: './app.component.html',
    styleUrls: ['./app.component.css']
})
export class AppComponent {
  title = 'Cosmos Voyager';
  
  screens = [
    { key: 'home', label: 'Home', route: '/home' },
    { key: 'explore', label: 'Explore', route: '/explore' },
    { key: 'profile', label: 'Profile & Memories', route: '/profile' },
    { key: 'trips', label: 'My Trips', route: '/trips' }
  ];

  constructor(public router: Router) {}
}
