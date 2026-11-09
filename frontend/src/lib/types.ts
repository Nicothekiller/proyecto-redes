export interface Node {
	node_id: string;
	overlay_ip: string;
	pubkey: string;
	endpoint: string;
	last_heartbeat: string;
	heartbeat_recent: boolean;
	heartbeat_age_s: number;
	connectivity_proven: boolean;
}

export interface Pair {
	reporter: string;
	peer: string;
	reporter_overlay_ip: string;
	peer_overlay_ip: string;
	endpoint: string | null;
	last_handshake: number;
	handshake_age_s: number | null;
	rx_bytes: number;
	tx_bytes: number;
	probe_ok: boolean | null;
	probe_rtt_ms: number | null;
	probe_ran_at: string | null;
	reported_at: string;
	connectivity_proven: boolean;
}

export interface Status {
	as_of: string;
	offline_after_s: number;
	probe_ttl_s: number;
	nodes_total: number;
	pairs: Pair[];
}

export interface Dashboard {
	nodes: Node[];
	status: Status;
	fetchedAt: string;
}
