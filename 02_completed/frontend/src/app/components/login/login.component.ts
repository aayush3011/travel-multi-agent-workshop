import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { TravelApiService } from '../../services/travel-api.service';
import { User } from '../../models/travel.models';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './login.component.html',
  styleUrls: ['./login.component.css']
})
export class LoginComponent implements OnInit {
  users: User[] = [];
  selectedUserId: string | null = null;
  showCreateForm = false;
  isLoading = false;
  errorMessage = '';

  // New user form
  newUser = {
    userId: '',
    name: '',
    email: '',
    phone: '',
    gender: '',
    age: undefined as number | undefined,
    address: {
      street: '',
      city: '',
      state: '',
      zip: '',
      country: ''
    }
  };

  constructor(
    private travelApiService: TravelApiService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.loadUsers();
  }

  loadUsers(): void {
    this.isLoading = true;
    this.travelApiService.getUsers().subscribe({
      next: (users) => {
        this.users = users;
        this.isLoading = false;
      },
      error: (error) => {
        console.error('Error loading users:', error);
        this.errorMessage = 'Failed to load users. Please try again.';
        this.isLoading = false;
      }
    });
  }

  onUserSelect(): void {
    // Just store the selected user ID, don't auto-login
    this.errorMessage = '';
  }

  onLogin(): void {
    if (!this.selectedUserId) {
      this.errorMessage = 'Please select a user first';
      return;
    }

    const user = this.users.find(u => u.userId === this.selectedUserId);
    if (user) {
      this.login(user);
    } else {
      this.errorMessage = 'Selected user not found';
    }
  }

  toggleCreateForm(): void {
    this.showCreateForm = !this.showCreateForm;
    this.errorMessage = '';
  }

  createNewUser(): void {
    // Validation
    if (!this.newUser.userId || !this.newUser.name || !this.newUser.email) {
      this.errorMessage = 'Please fill in all required fields (User ID, Name, Email)';
      return;
    }

    // Check if userId already exists
    if (this.users.some(u => u.userId === this.newUser.userId)) {
      this.errorMessage = 'User ID already exists. Please choose a different one.';
      return;
    }

    this.isLoading = true;
    this.errorMessage = '';

    this.travelApiService.createUser(this.newUser).subscribe({
      next: (user) => {
        console.log('User created successfully:', user);
        this.login(user);
      },
      error: (error) => {
        console.error('Error creating user:', error);
        this.errorMessage = 'Failed to create user. Please try again.';
        this.isLoading = false;
      }
    });
  }

  private login(user: User): void {
    this.travelApiService.setCurrentUser(user);
    this.router.navigate(['/explore']);
  }

  resetForm(): void {
    this.newUser = {
      userId: '',
      name: '',
      email: '',
      phone: '',
      gender: '',
      age: undefined,
      address: {
        street: '',
        city: '',
        state: '',
        zip: '',
        country: ''
      }
    };
    this.errorMessage = '';
  }
}
