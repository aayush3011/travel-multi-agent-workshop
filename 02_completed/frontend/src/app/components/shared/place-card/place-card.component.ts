import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Place } from '../../../models/travel.models';
import { ChipComponent } from '../chip/chip.component';

@Component({
    selector: 'app-place-card',
    imports: [CommonModule, ChipComponent],
    template: `
    <div class="rounded-2xl border overflow-hidden bg-white hover:shadow-lg transition-all cursor-pointer">
      <!-- Icon Header -->
      <div class="h-20 bg-gradient-to-br from-blue-50 to-indigo-50 grid place-items-center">
        <span class="text-5xl">{{ getIcon() }}</span>
      </div>
      
      <!-- Content -->
      <div class="p-4">
        <div class="font-semibold text-lg">{{ place.name }}</div>
        <div class="text-xs text-gray-500 mt-1">
          {{ place.neighborhood || place.geoScopeId }} · 
          {{ getPriceTierDisplay() }} · 
          ⭐ {{ place.rating?.toFixed(1) || 'N/A' }}
        </div>
        
        <!-- Tags -->
        <div class="mt-2 flex flex-wrap gap-1">
          <app-chip *ngFor="let tag of getTags()" [text]="tag"></app-chip>
        </div>
        
        <!-- Description (truncated) -->
        <p *ngIf="place.description" class="mt-2 text-xs text-gray-600 line-clamp-2">
          {{ place.description }}
        </p>
      </div>
    </div>
  `,
    styles: [`
    .line-clamp-2 {
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }
  `]
})
export class PlaceCardComponent {
  @Input() place!: Place;

  getTags(): string[] {
    // Return actual tags from the place, limited to 3
    return this.place.tags?.slice(0, 3) || [];
  }

  getIcon(): string {
    if (this.place.type === 'hotel') return '🏨';
    
    if (this.place.type === 'restaurant') {
      // Sub-categories for restaurants
      if (this.place.tags?.includes('cafe')) return '☕';
      if (this.place.tags?.includes('fine-dining')) return '🍷';
      return '🍽️';
    }
    
    if (this.place.type === 'activity') {
      // Different icons based on tags
      if (this.place.tags?.includes('museum')) return '🎨';
      if (this.place.tags?.includes('historic')) return '🏛️';
      if (this.place.tags?.includes('park')) return '🏞️';
      if (this.place.tags?.includes('beach')) return '🏖️';
      if (this.place.tags?.includes('monument')) return '🗿';
      if (this.place.tags?.includes('entertainment')) return '🎭';
      return '🎪';
    }
    
    return '📍';
  }

  getPriceTierDisplay(): string {
    const tier = this.place.priceTier;
    if (!tier) return '$$';
    switch (tier) {
      case 'budget': return '$';
      case 'moderate': return '$$';
      case 'upscale': return '$$$';
      case 'luxury': return '$$$$';
      default: return '$$';
    }
  }
}
