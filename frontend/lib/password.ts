/**
 * Password policy — mirrors `backend/app/core/security.py`.
 *
 * The backend validates every *new* password (create, change, reset)
 * with `validate_password_strength`:
 *
 *   - 10–128 characters
 *   - at least one lowercase letter
 *   - at least one uppercase letter
 *   - at least one digit
 *   - at least one special (non-alphanumeric) character
 *
 * The two MUST stay in sync. Before this module existed the app only
 * checked "8 characters", so a user could satisfy the client-side
 * check and still get a 422 from the API on password reset — the
 * screen said "Password must be at least 8 characters" and then
 * "Invalid or expired reset token" with no explanation.
 */

export const PASSWORD_MIN_LENGTH = 10;
export const PASSWORD_MAX_LENGTH = 128;

export const PASSWORD_POLICY_MESSAGE =
  `Password must be ${PASSWORD_MIN_LENGTH}–${PASSWORD_MAX_LENGTH} characters and contain ` +
  'at least one uppercase letter, one lowercase letter, one digit, and one special character';

const UPPER = /[A-Z]/;
const LOWER = /[a-z]/;
const DIGIT = /\d/;
const SPECIAL = /[^A-Za-z0-9]/;

/**
 * Returns `null` when the password satisfies the policy, otherwise a
 * human-readable reason it does not.
 */
export function checkPasswordStrength(password: string): string | null {
  if (password.length < PASSWORD_MIN_LENGTH) {
    return `Password must be at least ${PASSWORD_MIN_LENGTH} characters.`;
  }
  if (password.length > PASSWORD_MAX_LENGTH) {
    return `Password must be at most ${PASSWORD_MAX_LENGTH} characters.`;
  }
  if (!LOWER.test(password)) {
    return 'Password must include a lowercase letter.';
  }
  if (!UPPER.test(password)) {
    return 'Password must include an uppercase letter.';
  }
  if (!DIGIT.test(password)) {
    return 'Password must include a number.';
  }
  if (!SPECIAL.test(password)) {
    return 'Password must include a special character.';
  }
  return null;
}

/** `true` when the password satisfies the backend policy. */
export function isPasswordValid(password: string): boolean {
  return checkPasswordStrength(password) === null;
}
