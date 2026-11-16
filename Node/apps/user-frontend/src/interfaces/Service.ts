export interface IService {
    id: number | null;
    segment_id: string | number;
    name: string;
    description: string;
    currency: string;
    price: number;
    checked: boolean;
    mandatory: boolean;
}
