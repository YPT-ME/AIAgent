/**
 * User Session Management
 * Generates and stores a unique user ID in localStorage for thread isolation
 */

const USER_ID_KEY = 'lg:chat:userId';

/**
 * Generate a simple unique ID
 */
function generateUserId(): string {
  return `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

/**
 * Get or create a user ID from localStorage
 */
export function getUserId(): string {
  if (typeof window === 'undefined') {
    return 'server';
  }

  let userId = window.localStorage.getItem(USER_ID_KEY);
  
  if (!userId) {
    userId = generateUserId();
    window.localStorage.setItem(USER_ID_KEY, userId);
  }
  
  return userId;
}

/**
 * Clear the user session (for logout or reset)
 */
export function clearUserSession(): void {
  if (typeof window !== 'undefined') {
    window.localStorage.removeItem(USER_ID_KEY);
  }
}
