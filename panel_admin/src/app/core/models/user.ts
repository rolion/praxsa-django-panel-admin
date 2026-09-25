export class User {
  id!: number;
  username!: string;
  password!: string;
  firstName!: string;
  lastName!: string;
  token!: string;
  email?: string;
  isStaff?: boolean;
  groups?: string[];
}
