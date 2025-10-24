import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Message } from '../../../models/travel.models';

@Component({
    selector: 'app-message',
    imports: [CommonModule],
    template: `
    <div [ngClass]="message.role === 'user' ? 'justify-end' : 'justify-start'" class="flex gap-3">
      <!-- Assistant/System Avatar -->
      <div *ngIf="message.role !== 'user'" class="h-8 w-8 rounded-full bg-gray-200 grid place-items-center flex-shrink-0">
        {{ message.role === 'assistant' ? '🤖' : '🧭' }}
      </div>
      
      <!-- Message Bubble -->
      <div 
        [ngClass]="message.role === 'user' ? 'bg-black text-white' : 'bg-white'" 
        class="max-w-[70%] rounded-2xl px-4 py-3 border"
      >
        <div class="text-sm leading-relaxed whitespace-pre-wrap">{{ message.content }}</div>
        
        <!-- Agent metadata -->
        <div *ngIf="message.metadata && message.metadata.agent" class="mt-2 text-xs opacity-70">
          Agent: {{ message.metadata.agent }}
        </div>
      </div>
      
      <!-- User Avatar -->
      <div *ngIf="message.role === 'user'" class="h-8 w-8 rounded-full bg-gray-900 text-white grid place-items-center flex-shrink-0">
        U
      </div>
    </div>
  `
})
export class MessageComponent {
  @Input() message!: Message;
}
