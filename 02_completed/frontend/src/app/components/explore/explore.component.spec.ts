import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ExploreComponent } from './explore.component';
import { TravelApiService } from '../../services/travel-api.service';
import { of } from 'rxjs';
import { Place } from '../../models/travel.models';

describe('ExploreComponent', () => {
  let component: ExploreComponent;
  let fixture: ComponentFixture<ExploreComponent>;
  let mockApiService: jasmine.SpyObj<TravelApiService>;

  const mockPlaces: Place[] = [
    {
      id: '1',
      name: 'Test Hotel',
      type: 'hotel',
      description: 'A great hotel',
      geoScopeId: 'rome',
      rating: 4.5,
      priceTier: 'upscale',
      tags: ['luxury', 'central'],
      accessibility: ['wheelchair-friendly']
    },
    {
      id: '2',
      name: 'Test Restaurant',
      type: 'restaurant',
      description: 'Amazing food',
      geoScopeId: 'rome',
      rating: 4.8,
      priceTier: 'moderate',
      tags: ['italian', 'outdoor-seating'],
      accessibility: []
    }
  ];

  beforeEach(async () => {
    mockApiService = jasmine.createSpyObj('TravelApiService', [
      'searchPlaces',
      'sendMessage'
    ]);
    mockApiService.searchPlaces.and.returnValue(of(mockPlaces));
    mockApiService.sendMessage.and.returnValue(of({
      response: 'Hello! How can I help?',
      threadId: 'thread-1',
      messages: []
    }));

    await TestBed.configureTestingModule({
      imports: [ExploreComponent],
      providers: [
        { provide: TravelApiService, useValue: mockApiService }
      ]
    }).compileComponents();

    fixture = TestBed.createComponent(ExploreComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should initialize with default filters', () => {
    expect(component.filters).toBeDefined();
    expect(component.filters.placeType).toBe('all');
    expect(component.filters.budget).toBe('any');
  });

  it('should load places on init', () => {
    expect(component.places.length).toBeGreaterThan(0);
  });

  it('should have chat closed by default', () => {
    expect(component.chatOpen).toBe(false);
  });

  it('should open and close chat', () => {
    component.openChat();
    expect(component.chatOpen).toBe(true);
    component.closeChat();
    expect(component.chatOpen).toBe(false);
  });

  it('should apply filters when applyFilters is called', () => {
    component.filters.placeType = 'hotel';
    component.applyFilters();
    expect(mockApiService.searchPlaces).toHaveBeenCalledWith(
      jasmine.objectContaining({ placeType: 'hotel' })
    );
  });

  it('should reset filters', () => {
    component.filters.placeType = 'hotel';
    component.filters.budget = 'luxury';
    component.resetFilters();
    expect(component.filters.placeType).toBe('all');
    expect(component.filters.budget).toBe('any');
  });

  it('should send chat message', () => {
    component.newMessage = 'Show me hotels';
    component.sendMessage();
    expect(mockApiService.sendMessage).toHaveBeenCalled();
  });

  it('should clear chat input after sending message', () => {
    component.currentThread = { id: 'thread-1', threadId: 'thread-1', tenantId: 'test', userId: 'user1', title: 'Test', createdAt: new Date().toISOString(), lastMessageAt: new Date().toISOString() };
    component.newMessage = 'Show me hotels';
    component.sendMessage();
    expect(component.newMessage).toBe('');
  });

  it('should not send empty chat messages', () => {
    component.newMessage = '';
    component.sendMessage();
    expect(mockApiService.sendMessage).not.toHaveBeenCalled();
  });

  it('should add user message to chat on send', () => {
    component.currentThread = { id: 'thread-1', threadId: 'thread-1', tenantId: 'test', userId: 'user1', title: 'Test', createdAt: new Date().toISOString(), lastMessageAt: new Date().toISOString() };
    component.newMessage = 'Show me hotels';
    const initialLength = component.messages.length;
    component.sendMessage();
    expect(component.messages.length).toBeGreaterThan(initialLength);
  });

  it('should handle save place action', () => {
    const place = mockPlaces[0];
    component.onSavePlace(place);
    // Should not throw error
    expect(component).toBeTruthy();
  });

  it('should handle add to day action', () => {
    const place = mockPlaces[0];
    component.onAddToDay(place);
    // Should not throw error
    expect(component).toBeTruthy();
  });

  it('should handle swap place action', () => {
    const place = mockPlaces[0];
    component.onSwapPlace(place);
    // Should not throw error
    expect(component).toBeTruthy();
  });

  it('should render filters sidebar', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    const sidebar = compiled.querySelector('.w-64');
    expect(sidebar).toBeTruthy();
  });

  it('should render place grid', () => {
    component.places = mockPlaces;
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    const cards = compiled.querySelectorAll('app-place-card');
    expect(cards.length).toBe(2);
  });

  it('should render chat FAB when chat is closed', () => {
    component.chatOpen = false;
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    const fab = compiled.querySelector('.fixed.bottom-6.right-6');
    expect(fab).toBeTruthy();
  });

  it('should show chat drawer when chat is open', () => {
    component.chatOpen = true;
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    const drawer = compiled.querySelector('.fixed.top-0.right-0');
    expect(drawer).toBeTruthy();
  });
});
