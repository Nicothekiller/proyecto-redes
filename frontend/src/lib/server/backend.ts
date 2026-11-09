import { API_BASE_URL, API_KEY } from '$app/env/private';
import type { Dashboard, Node, Status } from '#lib/types.ts';

const BASE_URL = (API_BASE_URL ?? 'http://127.0.0.1:8000').replace(/\/+$/, '');
const TIMEOUT_MS = 4000;

export class BackendError extends Error {
	constructor(message: string) {
		super(message);
		this.name = 'BackendError';
	}
}

async function backendFetch<T>(path: string): Promise<T> {
	let response: Response;

	try {
		response = await fetch(`${BASE_URL}${path}`, {
			headers: {
				Authorization: `Bearer ${API_KEY}`,
				Accept: 'application/json'
			},
			signal: AbortSignal.timeout(TIMEOUT_MS)
		});
	} catch {
		throw new BackendError('no se pudo contactar al backend');
	}

	if (!response.ok) {
		if (response.status === 401 || response.status === 403) {
			throw new BackendError('el backend rechazó la API key configurada');
		}
		throw new BackendError(`el backend respondió con estado ${response.status}`);
	}

	return (await response.json()) as T;
}

export async function getNodes(): Promise<Node[]> {
	return backendFetch<Node[]>('/nodes');
}

export async function getStatus(): Promise<Status> {
	return backendFetch<Status>('/status');
}

export async function getDashboard(): Promise<Dashboard> {
	const [nodes, status] = await Promise.all([getNodes(), getStatus()]);
	return {
		nodes,
		status,
		fetchedAt: new Date().toISOString()
	};
}
