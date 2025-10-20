import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { ChipComponent } from '../shared/chip/chip.component';

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [CommonModule, ChipComponent],
  templateUrl: './home.component.html',
  styleUrls: ['./home.component.css']
})
export class HomeComponent {
  trendingThemes = [
    'Street Photography',
    'Coffee Culture',
    'Family-Friendly',
    'Night Markets',
    'Local Cuisine',
    'Historic Sites'
  ];

  constructor(private router: Router) {}

  startTrip(): void {
    this.router.navigate(['/explore']);
  }

  exploreCities(): void {
    this.router.navigate(['/explore']);
  }
}
