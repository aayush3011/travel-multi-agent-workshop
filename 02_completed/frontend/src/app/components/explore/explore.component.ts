import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subscription } from 'rxjs';
import { TravelApiService } from '../../services/travel-api.service';
import { Place, Thread, Message } from '../../models/travel.models';
import { PlaceCardComponent } from '../shared/place-card/place-card.component';
import { MessageComponent } from '../shared/message/message.component';

@Component({
    selector: 'app-explore',
    imports: [CommonModule, FormsModule, PlaceCardComponent, MessageComponent],
    templateUrl: './explore.component.html',
    styleUrls: ['./explore.component.css']
})
export class ExploreComponent implements OnInit, OnDestroy {
  places: Place[] = [];
  chatOpen = false;
  messages: Message[] = [];
  currentThread: Thread | null = null;
  newMessage = '';
  isLoading = false;
  
  // Filters
  filters = {
    theme: '',
    budget: 'any',
    dietary: 'any',
    accessibility: 'any',
    placeType: 'all'
  };

  private subscriptions = new Subscription();

  constructor(private travelApi: TravelApiService) {}

  ngOnInit(): void {
    // Subscribe to messages
    this.subscriptions.add(
      this.travelApi.messages$.subscribe(messages => {
        this.messages = messages;
      })
    );

    // Subscribe to current thread
    this.subscriptions.add(
      this.travelApi.currentThread$.subscribe(thread => {
        this.currentThread = thread;
      })
    );

    // Load some sample places
    this.loadSamplePlaces();
  }

  ngOnDestroy(): void {
    this.subscriptions.unsubscribe();
  }

  loadSamplePlaces(): void {
    // For demo purposes, create some mock places
    // In production, this would call the API
    this.places = this.createMockPlaces();
  }

  createMockPlaces(): Place[] {
    const mockPlaces: Place[] = [];
    for (let i = 1; i <= 9; i++) {
      mockPlaces.push({
        id: `place-${i}`,
        geoScopeId: 'barcelona',
        type: i % 3 === 0 ? 'hotel' : i % 3 === 1 ? 'restaurant' : 'attraction',
        name: `Amazing Place #${i}`,
        description: 'A wonderful location perfect for your trip. Experience local culture and great atmosphere.',
        neighborhood: 'Gothic Quarter',
        rating: 4.5 + (Math.random() * 0.5),
        priceTier: ['budget', 'moderate', 'upscale'][i % 3] as any,
        tags: ['cozy', 'popular', 'instagram-worthy'].slice(0, 2)
      });
    }
    return mockPlaces;
  }

  openChat(): void {
    if (!this.currentThread) {
      this.travelApi.createThread().subscribe({
        next: (thread) => {
          this.currentThread = thread;
          this.chatOpen = true;
        },
        error: (error) => {
          console.error('Error creating thread:', error);
          alert('Failed to start chat. Please ensure the backend is running.');
        }
      });
    } else {
      this.chatOpen = true;
    }
  }

  closeChat(): void {
    this.chatOpen = false;
  }

  sendMessage(): void {
    if (!this.newMessage.trim() || !this.currentThread) return;

    const userMessage = this.newMessage;
    this.newMessage = '';
    this.isLoading = true;

    // Optimistically add user message to UI
    this.messages = [...this.messages, { role: 'user', content: userMessage }];

    this.travelApi.sendMessage(this.currentThread.threadId, userMessage).subscribe({
      next: (response) => {
        this.messages = response.messages;
        this.isLoading = false;
      },
      error: (error) => {
        console.error('Error sending message:', error);
        this.isLoading = false;
        alert('Failed to send message. Please check your backend connection.');
      }
    });
  }

  onSavePlace(place: Place): void {
    console.log('Saving place:', place);
    alert(`Saved ${place.name} to your favorites!`);
  }

  onAddToDay(place: Place): void {
    console.log('Adding to day:', place);
    alert(`Added ${place.name} to your itinerary!`);
  }

  onSwapPlace(place: Place): void {
    console.log('Swapping place:', place);
    alert(`Finding similar places to ${place.name}...`);
  }

  applyFilters(): void {
    console.log('Applying filters:', this.filters);
    // In production, this would call the API with filters
    this.loadSamplePlaces();
  }

  resetFilters(): void {
    this.filters = {
      theme: '',
      budget: 'any',
      dietary: 'any',
      accessibility: 'any',
      placeType: 'all'
    };
    this.loadSamplePlaces();
  }
}
