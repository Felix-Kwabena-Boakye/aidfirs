import { z } from 'zod'

// User schemas
export const loginSchema = z.object({
  username: z.string().min(1, 'Username is required'),
  password: z.string().min(6, 'Password must be at least 6 characters')
})

export const registerSchema = z.object({
  username: z.string().min(3, 'Username must be at least 3 characters').regex(/^[a-zA-Z0-9_-]+$/, 'Username can only contain letters, numbers, _, -'),
  email: z.string().email('Invalid email address'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
  first_name: z.string().min(1, 'First name is required'),
  last_name: z.string().min(1, 'Last name is required'),
  role: z.enum(['investigator', 'analyst'], { message: 'Invalid role' })
})

export const caseSchema = z.object({
  case_number: z.string().min(1, 'Case number is required'),
  title: z.string().min(1, 'Title is required'),
  description: z.string(),
  priority: z.enum(['low', 'medium', 'high', 'critical']),
  status: z.enum(['open', 'in_progress', 'closed', 'archived'])
})

export const evidenceSchema = z.object({
  case_id: z.string(),
  evidence_type: z.enum(['file', 'disk_image', 'memory_dump', 'network_capture', 'log_file', 'registry', 'email', 'other']),
  file_name: z.string().min(1, 'File name is required'),
  description: z.string()
})

// Refine for file uploads
export const evidenceUploadSchema = evidenceSchema.refine((data) => data.file_name.trim() !== '', {
  message: 'File name cannot be empty',
  path: ['file_name']
})

