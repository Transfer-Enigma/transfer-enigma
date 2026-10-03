export interface UpdateResponse {
    routesCount: string;
    routesInsertedCount: string;
    warnings: any[];
    fixes?: Array<{ sheet: string; row: number; column: string; old: unknown; new: unknown }>;
    affected_rows?: AffectedRow[];
}

export interface SyncErrorItem {
    document?: string | null;
    sheet?: string | null;
    row?: number | null;
    cell?: string | null;
    code: string;
    message: string;
    severity?: string;
    details?: Record<string, unknown> | null;
    error?: string;
    rows_list?: Array<{ error: string; row_number: number; columns: string[] }>;
    row_numbers?: number[];
}

export interface ValidateResponse {
    errors: SyncErrorItem[];
    warnings: SyncErrorItem[];
    checked_rows: number;
    uids_written?: number;
    fixes?: Array<{ sheet: string; row: number; column: string; old: unknown; new: unknown }>;
    highlighted?: number;
    affected_rows?: AffectedRow[];
}

export interface AffectedRow {
    document?: string | null;
    scope: string;
    sheet: string;
    row: number;
    uid: string;
    values: Record<string, unknown>;
    fixed: boolean;
    errors: SyncErrorItem[];
    fixes: Array<{ sheet: string; row: number; column: string; old: unknown; new: unknown }>;
}

export interface SyncDocument {
    id: number;
    title: string;
    url: string;
    source_type: string;
    file_name: string | null;
    sea_ws: string | null;
    rail_ws: string | null;
    truck_ws: string | null;
    dropp_ws: string | null;
    points_ws: string | null;
    services_ws: string | null;
    uid_column: string;
    last_status: string | null;
    last_errors_count: number;
    loaded_at: string | null;
}

export interface RunSelection {
    document_id: number;
    sheets: string[] | "all";
}

export interface RunOptions {
    mode: "validate" | "sync";
    load_on_warnings: boolean;
    sync_mode: "all" | "new";
    fix: boolean;
    highlight: boolean;
    ensure_uids: boolean;
}

