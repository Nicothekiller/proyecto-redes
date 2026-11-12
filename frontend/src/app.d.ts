// See https://svelte.dev/docs/kit/types#app.d.ts
// for information about these interfaces
declare global {
	namespace App {
		// interface Error {}
		interface Locals {
			key: string;
			role: 'admin' | 'read';
		}
		// interface PageData {}
		// interface PageState {}
		// interface Platform {}
	}
}

export {};
