import { Component, OnInit, OnDestroy, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { Subscription } from 'rxjs';
import { TravelApiService } from '../../services/travel-api.service';
import { Place, Thread, Message, City } from '../../models/travel.models';
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
  
  // Trip Planning Fields (from Home component)
  selectedCity = '';
  currentCityName = ''; // Store the actual city name (not display name) for filtering
  startDate = '';
  endDate = '';
  travelers = {
    adults: 1,
    children: 0,
    pets: 0
  };

  // City Autocomplete
  cities: City[] = [];
  filteredCities: City[] = [];
  showCityDropdown = false;
  isLoadingCities = false;

  // Pickers
  showDatePicker = false;
  showTravelersPicker = false;
  
  // Filters - Updated to support multi-select
  filters = {
    theme: '',
    budget: [] as string[],        // Changed to array for multi-select
    dietary: [] as string[],        // Changed to array for multi-select
    accessibility: [] as string[],  // Changed to array for multi-select
    placeType: 'all'
  };

  private subscriptions = new Subscription();

  constructor(
    private travelApi: TravelApiService,
    private route: ActivatedRoute
  ) {}

  ngOnInit(): void {
    // Load cities for autocomplete
    this.loadCities();

    // Check for city query param
    this.route.queryParams.subscribe(params => {
      if (params['city']) {
        const cityName = params['city'];
        // Find and select the city
        this.travelApi.getCities().subscribe(cities => {
          const city = cities.find(c => c.name === cityName);
          if (city) {
            this.selectedCity = city.displayName;
            this.loadPlacesForCity(city.name);
          }
        });
      }
    });

    // Subscribe to selected city from service
    this.subscriptions.add(
      this.travelApi.selectedCity$.subscribe(city => {
        if (city) {
          // Find the city object to get the display name
          const cityObj = this.cities.find(c => c.name === city);
          if (cityObj) {
            this.selectedCity = cityObj.displayName; // Use display name instead of snake_case
          } else {
            this.selectedCity = this.formatCityName(city); // Fallback to formatting
          }
          this.loadPlacesForCity(city);
        }
      })
    );

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

    // Don't load any places initially - wait for user to select city and click "Start a trip"
    // this.loadSamplePlaces();
  }

  ngOnDestroy(): void {
    this.subscriptions.unsubscribe();
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

    // Use sessionId (fallback to threadId for backward compatibility)
    const threadId = this.currentThread.sessionId || this.currentThread.threadId || '';
    
    if (!threadId) {
      console.error('No thread ID available');
      this.isLoading = false;
      return;
    }
    
    console.log('📤 Sending message to thread:', threadId);
    
    this.travelApi.sendMessage(threadId, userMessage).subscribe({
      next: (response) => {
        console.log('📥 Received response:', response);
        
        // Backend returns messages array directly (not wrapped in object)
        if (Array.isArray(response)) {
          this.messages = response.map(msg => ({
            role: msg.senderRole === 'User' ? 'user' : 'assistant',
            content: msg.text || msg.content || '',
            timestamp: msg.timeStamp
          }));
        } else if (response.messages && Array.isArray(response.messages)) {
          this.messages = response.messages;
        } else {
          console.warn('Unexpected response format:', response);
        }
        this.isLoading = false;
      },
      error: (error) => {
        console.error('❌ Error sending message:', error);
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
    // Check if we have a current city loaded
    if (!this.currentCityName) {
      console.log('No city loaded yet, cannot apply filters');
      return;
    }

    this.isLoading = true;
    
    // If theme is provided, use vector search via /places/search
    if (this.filters.theme && this.filters.theme.trim()) {
      console.log('🎨 Using theme-based vector search:', this.filters.theme);
      
      const currentUser = this.travelApi.getCurrentUser();
      const searchRequest: any = {
        geoScope: this.currentCityName,
        query: this.filters.theme.trim(),
        userId: currentUser?.userId || 'guest',
        tenantId: this.travelApi.getTenantId(),
        filters: {
          type: this.filters.placeType !== 'all' ? this.filters.placeType : undefined,
          dietary: this.filters.dietary.length > 0 ? this.filters.dietary : undefined,
          accessibility: this.filters.accessibility.length > 0 ? this.filters.accessibility : undefined
        }
      };

      // Add priceTier filter (only single value supported by backend)
      if (this.filters.budget.length === 1) {
        searchRequest.filters.priceTier = this.filters.budget[0];
      }

      console.log('🔍 Search request:', searchRequest);

      this.travelApi.searchPlaces(searchRequest).subscribe({
        next: (places) => {
          let filteredPlaces = places;
          
          // Apply client-side filter for multiple price tiers (since vector search only supports one priceTier)
          if (this.filters.budget.length > 1) {
            filteredPlaces = filteredPlaces.filter(place => 
              place.priceTier && this.filters.budget.includes(place.priceTier)
            );
          }

          this.places = filteredPlaces;
          this.isLoading = false;
          console.log(`✅ Theme search completed, got ${filteredPlaces.length} places`);
        },
        error: (error) => {
          console.error('Error in theme search:', error);
          this.isLoading = false;
        }
      });
      
      return;
    }

    // Original filter logic (no theme) - use /places/filter endpoint
    const filterRequest: any = {
      city: this.currentCityName,
      types: this.filters.placeType !== 'all' ? [this.filters.placeType] : undefined,
      priceTiers: this.filters.budget.length > 0 ? this.filters.budget : undefined,
      dietary: this.filters.dietary.length > 0 ? this.filters.dietary : undefined,
      accessibility: this.filters.accessibility.length > 0 ? this.filters.accessibility : undefined
    };

    console.log('🔍 Filter request:', filterRequest);
    console.log('🔍 filters.placeType:', this.filters.placeType);
    console.log('🔍 Sending types array:', filterRequest.types);

    this.travelApi.filterPlaces(filterRequest).subscribe({
      next: (places) => {
        this.places = places;
        this.isLoading = false;
        console.log(`✅ Applied filters, got ${places.length} places`);
        console.log('📍 First few places:', places.slice(0, 3).map(p => ({name: p.name, type: p.type})));
      },
      error: (error) => {
        console.error('Error applying filters:', error);
        this.isLoading = false;
      }
    });
  }

  resetFilters(): void {
    this.filters = {
      theme: '',
      budget: [],
      dietary: [],
      accessibility: [],
      placeType: 'all'
    };
    // Re-apply filters with reset values
    this.applyFilters();
  }

  // Multi-select filter toggle methods
  toggleBudgetFilter(tier: string): void {
    const index = this.filters.budget.indexOf(tier);
    if (index > -1) {
      this.filters.budget.splice(index, 1);
    } else {
      this.filters.budget.push(tier);
    }
    this.applyFilters();
  }

  toggleDietaryFilter(option: string): void {
    const index = this.filters.dietary.indexOf(option);
    if (index > -1) {
      this.filters.dietary.splice(index, 1);
    } else {
      this.filters.dietary.push(option);
    }
    this.applyFilters();
  }

  toggleAccessibilityFilter(option: string): void {
    const index = this.filters.accessibility.indexOf(option);
    if (index > -1) {
      this.filters.accessibility.splice(index, 1);
    } else {
      this.filters.accessibility.push(option);
    }
    this.applyFilters();
  }

  // City/Dates/Travelers Methods (from Home component)
  loadCities(): void {
    this.isLoadingCities = true;
    this.travelApi.getCities().subscribe({
      next: (cities) => {
        this.cities = cities;
        this.filteredCities = cities;
        this.isLoadingCities = false;
      },
      error: (error) => {
        console.error('Error loading cities:', error);
        this.isLoadingCities = false;
      }
    });
  }

  onCityInputChange(): void {
    if (!this.selectedCity) {
      this.filteredCities = this.cities;
      this.showCityDropdown = true;
      return;
    }

    const searchTerm = this.selectedCity.toLowerCase();
    this.filteredCities = this.cities.filter(city =>
      city.displayName.toLowerCase().includes(searchTerm) ||
      city.name.toLowerCase().includes(searchTerm)
    );
    this.showCityDropdown = true;
  }

  onCityFocus(): void {
    this.showCityDropdown = true;
  }

  onCityBlur(): void {
    setTimeout(() => {
      this.showCityDropdown = false;
    }, 200);
  }

  selectCity(city: City): void {
    this.selectedCity = city.displayName; // Keep the display name for UI
    this.showCityDropdown = false;
    // Don't update service yet - wait for "Start a trip" button
  }

  // Date Picker Methods
  toggleDatePicker(): void {
    this.showDatePicker = !this.showDatePicker;
    this.showTravelersPicker = false;
    this.showCityDropdown = false;
  }

  closeDatePicker(): void {
    this.showDatePicker = false;
  }

  getDateRangeDisplay(): string {
    if (!this.startDate && !this.endDate) {
      return 'Add dates';
    }
    if (this.startDate && !this.endDate) {
      return this.formatDate(this.startDate);
    }
    if (this.startDate && this.endDate) {
      return `${this.formatDate(this.startDate)} - ${this.formatDate(this.endDate)}`;
    }
    return 'Add dates';
  }

  private formatDate(dateString: string): string {
    if (!dateString) return '';
    // Parse as UTC to avoid timezone shifting
    const [year, month, day] = dateString.split('-').map(Number);
    const date = new Date(year, month - 1, day); // month is 0-indexed
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  }

  // Format city name for display (abu_dhabi -> Abu Dhabi)
  formatCityName(cityName: string): string {
    if (!cityName) return '';
    return cityName
      .split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1))
      .join(' ');
  }

  // Travelers Picker Methods
  toggleTravelersPicker(): void {
    this.showTravelersPicker = !this.showTravelersPicker;
    this.showDatePicker = false;
    this.showCityDropdown = false;
  }

  closeTravelersPicker(): void {
    this.showTravelersPicker = false;
  }

  getTravelersDisplay(): string {
    const parts: string[] = [];
    
    if (this.travelers.adults > 0) {
      parts.push(`${this.travelers.adults} adult${this.travelers.adults !== 1 ? 's' : ''}`);
    }
    if (this.travelers.children > 0) {
      parts.push(`${this.travelers.children} child${this.travelers.children !== 1 ? 'ren' : ''}`);
    }
    if (this.travelers.pets > 0) {
      parts.push(`${this.travelers.pets} pet${this.travelers.pets !== 1 ? 's' : ''}`);
    }
    
    return parts.length > 0 ? parts.join(', ') : '1 adult';
  }

  incrementAdults(): void {
    if (this.travelers.adults < 10) {
      this.travelers.adults++;
    }
  }

  decrementAdults(): void {
    if (this.travelers.adults > 1) {
      this.travelers.adults--;
    }
  }

  incrementChildren(): void {
    if (this.travelers.children < 10) {
      this.travelers.children++;
    }
  }

  decrementChildren(): void {
    if (this.travelers.children > 0) {
      this.travelers.children--;
    }
  }

  incrementPets(): void {
    if (this.travelers.pets < 5) {
      this.travelers.pets++;
    }
  }

  decrementPets(): void {
    if (this.travelers.pets > 0) {
      this.travelers.pets--;
    }
  }

  // Start Trip - Filter places by selected city
  startTrip(): void {
    console.log('🚀 startTrip() called');
    console.log('Selected city:', this.selectedCity);
    console.log('Available cities:', this.cities);
    
    if (!this.selectedCity) {
      alert('Please select a city first');
      return;
    }

    const city = this.cities.find(c => 
      c.displayName === this.selectedCity
    );

    console.log('Found city object:', city);

    if (city) {
      console.log('Loading places for city:', city.name);
      this.currentCityName = city.name; // Store the city name for filtering
      this.loadPlacesForCity(city.name);
      this.travelApi.setSelectedCity(city.name);
    } else {
      console.error('❌ City not found in cities array!');
      alert('City not found. Please select from the dropdown.');
    }
  }

  loadPlacesForCity(cityName: string): void {
    console.log('Loading places for city:', cityName);
    this.isLoading = true;
    
    // Call API to fetch real places
    const filterRequest: any = {
      city: cityName,
      types: this.filters.placeType !== 'all' ? [this.filters.placeType] : undefined,
      priceTiers: this.filters.budget.length > 0 ? this.filters.budget : undefined,
      dietary: this.filters.dietary.length > 0 ? this.filters.dietary : undefined,
      accessibility: this.filters.accessibility.length > 0 ? this.filters.accessibility : undefined
    };

    this.travelApi.filterPlaces(filterRequest).subscribe({
      next: (places) => {
        this.places = places;
        this.isLoading = false;
        console.log(`✅ Loaded ${places.length} places for ${cityName}`);
      },
      error: (error) => {
        console.error('Error loading places:', error);
        this.isLoading = false;
        this.places = []; // Clear places on error
        alert('Failed to load places. Please check your backend connection.');
      }
    });
  }

  @HostListener('document:click', ['$event'])
  onDocumentClick(event: MouseEvent): void {
    const target = event.target as HTMLElement;
    
    // Close dropdowns if clicking outside
    if (!target.closest('.trip-planning-bar')) {
      this.showCityDropdown = false;
      this.showDatePicker = false;
      this.showTravelersPicker = false;
    }
  }
}
