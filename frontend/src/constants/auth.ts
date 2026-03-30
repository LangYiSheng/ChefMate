export const USERNAME_RULE = {
  minLength: 4,
  maxLength: 20,
  pattern: /^[A-Za-z][A-Za-z0-9_]{3,19}$/,
  hint: '4-20 位，字母开头，可使用字母、数字和下划线',
}

export const PASSWORD_RULE = {
  minLength: 8,
  maxLength: 32,
  pattern: /^(?=.*[A-Za-z])(?=.*\d)[A-Za-z\d~!@#$%^&*_\-+=.?]{8,32}$/,
  hint: '8-32 位，至少包含 1 个字母和 1 个数字，可使用常见符号',
}

export const EMAIL_RULE = {
  pattern: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
}

export function validateUsername(username: string) {
  return USERNAME_RULE.pattern.test(username.trim())
}

export function validatePassword(password: string) {
  return PASSWORD_RULE.pattern.test(password)
}

export function validateOptionalEmail(email: string) {
  const normalizedEmail = email.trim()
  if (!normalizedEmail) {
    return true
  }

  return EMAIL_RULE.pattern.test(normalizedEmail)
}
