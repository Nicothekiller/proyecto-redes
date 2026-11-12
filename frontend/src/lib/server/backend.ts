import { API_BASE_URL } from '$app/env/private';
import type { Dashboard, Node, Status } from '#lib/types.ts';

const BASE_URL = (API_BASE_URL ?? 'http://127.0.0.1:8000').replace(/\/+$/, '');
const TIMEOUT_MS = 4000;

export class BackendError extends Error {
	constructor(
		message: string,
		public status = 502
	) {
		super(message);
		this.name = 'BackendError';
	}
}

async function backendFetch<T>(path: string, key: string, method = 'GET'): Promise<T> {
	let response: Response;

	try {
		response = await fetch(`${BASE_URL}${path}`, {
			method,
			headers: {
				Authorization: `Bearer ${key}`,
				Accept: 'application/json'
			},
			signal: AbortSignal.timeout(TIMEOUT_MS)
		});
	} catch {
		throw new BackendError('no se pudo contactar al backend');
	}

	if (!response.ok) {
		if (response.status === 401 || response.status === 403) {
			throw new BackendError('clave inválida', response.status);
		}
		throw new BackendError(`el backend respondió con estado ${response.status}`, response.status);
	}

	return response.status === 204 ? (undefined as T) : ((await response.json()) as T);
}

export async function getRole(key: string): Promise<'admin' | 'read'> {
	const session = await backendFetch<{ role: 'admin' | 'read' }>('/dashboard/session', key);
	return session.role;
}

export async function deleteNode(key: string, nodeId: string): Promise<void> {
	return backendFetch<void>(`/nodes/${encodeURIComponent(nodeId)}`, key, 'DELETE');
}

export async function getDashboard(key: string): Promise<Dashboard> {
	const [nodes, status] = await Promise.all([
		backendFetch<Node[]>('/nodes', key),
		backendFetch<Status>('/status', key)
	]);
	return {
		nodes,
		status,
		fetchedAt: new Date().toISOString()
	};
}
