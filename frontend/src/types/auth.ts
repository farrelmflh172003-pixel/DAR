export type UserRole = 'Admin' | 'Superadmin' | 'Viewer' | 'Menteri' | 'Development';

export interface User {
  username: string;
  name: string;
  role: UserRole;
  avatar: string;
  description: string;
  is_protected: boolean;
}


export interface CaptchaData {
  captcha_id: string;
  question: string;
  svg: string;
}
