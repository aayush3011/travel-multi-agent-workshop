import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { TravelApiService } from '../../services/travel-api.service';
import { Memory } from '../../models/travel.models';

@Component({
    selector: 'app-profile',
    imports: [CommonModule, FormsModule],
    templateUrl: './profile.component.html',
    styleUrls: ['./profile.component.css']
})
export class ProfileComponent implements OnInit {
  memories: Memory[] = [];
  
  preferences = {
    budget: 'moderate',
    mobility: 'walk',
    dietary: 'any',
    timeOfDay: 'any'
  };

  pastHighlights = [
    { destination: 'Kyoto', experience: 'Morning markets', date: 'May 2024' },
    { destination: 'Barcelona', experience: 'Late-night cafés', date: 'Aug 2025' },
    { destination: 'Tokyo', experience: 'Street photography', date: 'Dec 2024' }
  ];

  constructor(private travelApi: TravelApiService) {}

  ngOnInit(): void {
    this.loadMemories();
  }

  loadMemories(): void {
    this.travelApi.getMemories().subscribe({
      next: (memories) => {
        this.memories = memories;
      },
      error: (error) => {
        console.error('Error loading memories:', error);
      }
    });
  }

  savePreferences(): void {
    console.log('Saving preferences:', this.preferences);
    alert('Preferences saved! These will be used for future recommendations.');
  }

  deleteMemory(memory: Memory): void {
    if (confirm(`Delete memory: ${memory.key}?`)) {
      this.travelApi.deleteMemory(memory.memoryId).subscribe({
        next: () => {
          this.memories = this.memories.filter(m => m.memoryId !== memory.memoryId);
          alert('Memory deleted successfully');
        },
        error: (error) => {
          console.error('Error deleting memory:', error);
          alert('Failed to delete memory');
        }
      });
    }
  }
}
