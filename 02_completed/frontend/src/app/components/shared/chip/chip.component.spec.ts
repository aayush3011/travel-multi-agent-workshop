import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ChipComponent } from './chip.component';

describe('ChipComponent', () => {
  let component: ChipComponent;
  let fixture: ComponentFixture<ChipComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [ChipComponent]
    }).compileComponents();

    fixture = TestBed.createComponent(ChipComponent);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should display text', () => {
    component.text = 'Test Chip';
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.textContent).toContain('Test Chip');
  });

  it('should render span element', () => {
    component.text = 'Test';
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    const span = compiled.querySelector('span');
    expect(span).toBeTruthy();
  });

  it('should apply default styling', () => {
    component.text = 'Default';
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    const span = compiled.querySelector('span');
    expect(span?.className).toContain('rounded-full');
    expect(span?.className).toContain('border');
  });

  it('should update text when input changes', () => {
    component.text = 'Initial';
    fixture.detectChanges();
    let compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.textContent).toContain('Initial');
    
    component.text = 'Updated';
    fixture.detectChanges();
    compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.textContent).toContain('Updated');
  });

  it('should handle empty text', () => {
    component.text = '';
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    const span = compiled.querySelector('span');
    expect(span).toBeTruthy();
    expect(span?.textContent?.trim()).toBe('');
  });
});
