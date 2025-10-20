import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
    selector: 'app-chip',
    imports: [CommonModule],
    template: `
    <span class="inline-flex items-center rounded-full border px-2 py-0.5 text-xs mr-2 mb-2 bg-white hover:bg-gray-50 transition">
      {{ text }}
    </span>
  `
})
export class ChipComponent {
  @Input() text: string = '';
}
