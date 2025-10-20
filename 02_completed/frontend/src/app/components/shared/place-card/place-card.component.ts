import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Place } from '../../../models/travel.models';
import { ChipComponent } from '../chip/chip.component';

@Component({
  selector: 'app-place-card',
  standalone: true,
  imports: [CommonModule, ChipComponent],
  template: `
    <div class="rounded-2xl border overflow-hidden bg-white hover:shadow-lg transition-all">
      <!-- Image Placeholder -->
      <div class="h-32 bg-gradient-to-br from-blue-100 to-blue-50 grid place-items-center text-gray-400">
        <span class="text-4xl">{{ getEmoji() }}</span>
      </div>
      
      <!-- Content -->
      <div class="p-3">
        <div class="font-semibold">{{ place.name }}</div>
        <div class="text-xs text-gray-500 mt-1">
          {{ place.neighborhood || place.geoScopeId }} · 
          {{ getPriceTierDisplay() }} · 
          ⭐ {{ place.rating || 'N/A' }}
        </div>
        
        <!-- Tags -->
        <div class="mt-2 flex flex-wrap gap-1">
          <app-chip *ngFor="let tag of (place.tags || []).slice(0, 3)" [text]="tag"></app-chip>
        </div>
        
        <!-- Description (truncated) -->
        <p class="mt-2 text-xs text-gray-600 line-clamp-2">
          {{ place.description }}
        </p>
        
        <!-- Actions -->
        <div class="mt-3 flex flex-wrap gap-2">
          <button 
            (click)="onSave()"
            class="px-2.5 py-1.5 rounded-lg border border-cosmos-primary text-cosmos-primary text-sm hover:bg-cosmos-primary hover:text-white transition"
          >
            Save
          </button>
          <button 
            (click)="onAddToDay()"
            class="px-2.5 py-1.5 rounded-lg border border-cosmos-primary text-cosmos-primary text-sm hover:bg-cosmos-primary hover:text-white transition"
          >
            Add to Day
          </button>
          <button 
            (click)="onSwap()"
            class="px-2.5 py-1.5 rounded-lg border border-gray-300 text-gray-600 text-sm hover:bg-gray-100 transition"
          >
            Swap
          </button>
        </div>
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
  @Output() save = new EventEmitter<Place>();
  @Output() addToDay = new EventEmitter<Place>();
  @Output() swap = new EventEmitter<Place>();

  getEmoji(): string {
    switch (this.place.type) {
      case 'hotel': return '🏨';
      case 'restaurant': return '🍽️';
      case 'attraction': return '🎭';
      default: return '📍';
    }
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

  onSave(): void {
    this.save.emit(this.place);
  }

  onAddToDay(): void {
    this.addToDay.emit(this.place);
  }

  onSwap(): void {
    this.swap.emit(this.place);
  }
}
