import { ComponentFixture, TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { AppComponent } from './app.component';
import { provideRouter } from '@angular/router';
import { routes } from './app.routes';

describe('AppComponent', () => {
  let component: AppComponent;
  let fixture: ComponentFixture<AppComponent>;
  let router: Router;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [AppComponent],
      providers: [provideRouter(routes)]
    }).compileComponents();

    fixture = TestBed.createComponent(AppComponent);
    component = fixture.componentInstance;
    router = TestBed.inject(Router);
    fixture.detectChanges();
  });

  it('should create the app', () => {
    expect(component).toBeTruthy();
  });

  it('should have title "Cosmos Voyager"', () => {
    expect(component.title).toEqual('Cosmos Voyager');
  });

  it('should have navigation screens defined', () => {
    expect(component.screens).toBeDefined();
    expect(component.screens.length).toBe(4);
  });

  it('should contain home screen', () => {
    const homeScreen = component.screens.find(s => s.key === 'home');
    expect(homeScreen).toBeDefined();
    expect(homeScreen?.label).toBe('Home');
    expect(homeScreen?.route).toBe('/home');
  });

  it('should contain explore screen', () => {
    const exploreScreen = component.screens.find(s => s.key === 'explore');
    expect(exploreScreen).toBeDefined();
    expect(exploreScreen?.label).toBe('Explore');
    expect(exploreScreen?.route).toBe('/explore');
  });

  it('should contain profile screen', () => {
    const profileScreen = component.screens.find(s => s.key === 'profile');
    expect(profileScreen).toBeDefined();
    expect(profileScreen?.label).toBe('Profile & Memories');
    expect(profileScreen?.route).toBe('/profile');
  });

  it('should contain trips screen', () => {
    const tripsScreen = component.screens.find(s => s.key === 'trips');
    expect(tripsScreen).toBeDefined();
    expect(tripsScreen?.label).toBe('My Trips');
    expect(tripsScreen?.route).toBe('/trips');
  });

  it('should render top bar with title', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    const title = compiled.querySelector('.text-cosmos-primary');
    expect(title?.textContent).toContain('Cosmos Voyager');
  });

  it('should render navigation tabs', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    const navLinks = compiled.querySelectorAll('a[routerLink]');
    expect(navLinks.length).toBe(4);
  });

  it('should have router outlet', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    const outlet = compiled.querySelector('router-outlet');
    expect(outlet).toBeTruthy();
  });

  it('should render footer', () => {
    const compiled = fixture.nativeElement as HTMLElement;
    const footer = compiled.querySelector('footer');
    expect(footer?.textContent).toContain('© 2025 Cosmos Voyager');
  });
});
