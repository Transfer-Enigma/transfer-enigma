export interface IRate {
    id: number;
    code: string;
    rate: number;
    date: string;
    created_at: string;
}

export interface IRatePayload {
    code: string;
    rate: number;
    date: string;
}
