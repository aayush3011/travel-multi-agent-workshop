import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Observable, BehaviorSubject } from 'rxjs';
import { tap } from 'rxjs/operators';
import {
  Thread,
  Message,
  Place,
  Trip,
  Memory,
  ChatCompletionResponse,
  PlaceSearchRequest
} from '../models/travel.models';

@Injectable({
  providedIn: 'root'
})
export class TravelApiService {
  private baseUrl = '/api';
  private tenantId = 'demo-tenant';
  private userId = 'demo-user';

  // State management
  private currentThreadSubject = new BehaviorSubject<Thread | null>(null);
  public currentThread$ = this.currentThreadSubject.asObservable();

  private messagesSubject = new BehaviorSubject<Message[]>([]);
  public messages$ = this.messagesSubject.asObservable();

  private threadsSubject = new BehaviorSubject<Thread[]>([]);
  public threads$ = this.threadsSubject.asObservable();

  constructor(private http: HttpClient) {
    this.loadThreads();
  }

  private getHeaders(): HttpHeaders {
    return new HttpHeaders({
      'Content-Type': 'application/json'
    });
  }

  // ============================================================================
  // Thread Management
  // ============================================================================

  loadThreads(): void {
    this.http.get<Thread[]>(
      `${this.baseUrl}/tenant/${this.tenantId}/user/${this.userId}/threads`,
      { headers: this.getHeaders() }
    ).subscribe({
      next: (threads) => this.threadsSubject.next(threads),
      error: (error) => console.error('Error loading threads:', error)
    });
  }

  createThread(): Observable<Thread> {
    return this.http.post<Thread>(
      `${this.baseUrl}/tenant/${this.tenantId}/user/${this.userId}/threads`,
      {},
      { headers: this.getHeaders() }
    ).pipe(
      tap(thread => {
        this.currentThreadSubject.next(thread);
        const threads = this.threadsSubject.value;
        this.threadsSubject.next([thread, ...threads]);
      })
    );
  }

  getThread(threadId: string): Observable<Thread> {
    return this.http.get<Thread>(
      `${this.baseUrl}/tenant/${this.tenantId}/user/${this.userId}/threads/${threadId}`,
      { headers: this.getHeaders() }
    ).pipe(
      tap(thread => this.currentThreadSubject.next(thread))
    );
  }

  getThreadMessages(threadId: string): Observable<Message[]> {
    return this.http.get<Message[]>(
      `${this.baseUrl}/tenant/${this.tenantId}/user/${this.userId}/threads/${threadId}/messages`,
      { headers: this.getHeaders() }
    ).pipe(
      tap(messages => this.messagesSubject.next(messages))
    );
  }

  renameThread(threadId: string, newTitle: string): Observable<Thread> {
    return this.http.patch<Thread>(
      `${this.baseUrl}/tenant/${this.tenantId}/user/${this.userId}/threads/${threadId}`,
      { title: newTitle },
      { headers: this.getHeaders() }
    );
  }

  deleteThread(threadId: string): Observable<any> {
    return this.http.delete(
      `${this.baseUrl}/tenant/${this.tenantId}/user/${this.userId}/threads/${threadId}`,
      { headers: this.getHeaders() }
    ).pipe(
      tap(() => {
        const threads = this.threadsSubject.value.filter(t => t.threadId !== threadId);
        this.threadsSubject.next(threads);
        if (this.currentThreadSubject.value?.threadId === threadId) {
          this.currentThreadSubject.next(null);
          this.messagesSubject.next([]);
        }
      })
    );
  }

  setCurrentThread(thread: Thread): void {
    this.currentThreadSubject.next(thread);
    if (thread) {
      this.getThreadMessages(thread.threadId).subscribe();
    } else {
      this.messagesSubject.next([]);
    }
  }

  // ============================================================================
  // Chat Completion
  // ============================================================================

  sendMessage(threadId: string, message: string): Observable<ChatCompletionResponse> {
    return this.http.post<ChatCompletionResponse>(
      `${this.baseUrl}/tenant/${this.tenantId}/user/${this.userId}/threads/${threadId}/completion`,
      JSON.stringify(message),
      { headers: this.getHeaders() }
    ).pipe(
      tap(response => {
        if (response.messages) {
          this.messagesSubject.next(response.messages);
        }
      })
    );
  }

  // ============================================================================
  // Places
  // ============================================================================

  searchPlaces(request: PlaceSearchRequest): Observable<Place[]> {
    return this.http.post<Place[]>(
      `${this.baseUrl}/tenant/${this.tenantId}/user/${this.userId}/places/search`,
      request,
      { headers: this.getHeaders() }
    );
  }

  // ============================================================================
  // Trips
  // ============================================================================

  getTrips(): Observable<Trip[]> {
    return this.http.get<Trip[]>(
      `${this.baseUrl}/tenant/${this.tenantId}/user/${this.userId}/trips`,
      { headers: this.getHeaders() }
    );
  }

  getTrip(tripId: string): Observable<Trip> {
    return this.http.get<Trip>(
      `${this.baseUrl}/tenant/${this.tenantId}/user/${this.userId}/trips/${tripId}`,
      { headers: this.getHeaders() }
    );
  }

  createTrip(trip: Partial<Trip>): Observable<Trip> {
    return this.http.post<Trip>(
      `${this.baseUrl}/tenant/${this.tenantId}/user/${this.userId}/trips`,
      trip,
      { headers: this.getHeaders() }
    );
  }

  updateTrip(tripId: string, trip: Partial<Trip>): Observable<Trip> {
    return this.http.put<Trip>(
      `${this.baseUrl}/tenant/${this.tenantId}/user/${this.userId}/trips/${tripId}`,
      trip,
      { headers: this.getHeaders() }
    );
  }

  deleteTrip(tripId: string): Observable<any> {
    return this.http.delete(
      `${this.baseUrl}/tenant/${this.tenantId}/user/${this.userId}/trips/${tripId}`,
      { headers: this.getHeaders() }
    );
  }

  // ============================================================================
  // Memories
  // ============================================================================

  getMemories(): Observable<Memory[]> {
    return this.http.get<Memory[]>(
      `${this.baseUrl}/tenant/${this.tenantId}/user/${this.userId}/memories`,
      { headers: this.getHeaders() }
    );
  }

  createMemory(memory: Partial<Memory>): Observable<Memory> {
    return this.http.post<Memory>(
      `${this.baseUrl}/tenant/${this.tenantId}/user/${this.userId}/memories`,
      memory,
      { headers: this.getHeaders() }
    );
  }

  deleteMemory(memoryId: string): Observable<any> {
    return this.http.delete(
      `${this.baseUrl}/tenant/${this.tenantId}/user/${this.userId}/memories/${memoryId}`,
      { headers: this.getHeaders() }
    );
  }

  // ============================================================================
  // Health & Status
  // ============================================================================

  getHealthStatus(): Observable<any> {
    return this.http.get(`${this.baseUrl}/health/ready`, { headers: this.getHeaders() });
  }

  getSystemStatus(): Observable<any> {
    return this.http.get(`${this.baseUrl}/status`, { headers: this.getHeaders() });
  }
}
