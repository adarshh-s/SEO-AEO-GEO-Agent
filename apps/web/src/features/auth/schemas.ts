import { z } from "zod";

// Messages are i18n keys in the "auth" namespace; the UI translates them.
export const emailField = z.string().trim().min(1, "validation.required").email("validation.email");
export const passwordField = z.string().min(10, "validation.passwordLength").max(200);

export const loginSchema = z.object({
  email: emailField,
  password: z.string().min(1, "validation.required"),
});
export const signupSchema = z.object({
  full_name: z.string().trim().min(1, "validation.required").max(200),
  org_name: z.string().trim().max(200).optional(),
  email: emailField,
  password: passwordField,
});
export const forgotSchema = z.object({ email: emailField });
export const resetSchema = z
  .object({ password: passwordField, confirm: z.string() })
  .refine((v) => v.password === v.confirm, {
    message: "validation.passwordMatch",
    path: ["confirm"],
  });

export type LoginValues = z.infer<typeof loginSchema>;
export type SignupValues = z.infer<typeof signupSchema>;
