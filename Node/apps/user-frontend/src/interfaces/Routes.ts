import type { IService } from "./Service";

export type RouteExtendedDescriptor = [
    RouteDescriptor,
    // boolean = selected in commercial proposal
    [PriceDescriptor, PriceDescriptor, boolean],
];
export type PriceDescriptor = number | PriceRange;
export type PriceRange = [number, number];
export type RouteDescriptor = [Route, IDrop, boolean, IService[]];  // boolean = isEffective
export type Route = (ISinglePriceSegment | IMultiPriceSegment)[];

export enum RouteType {
    SEA = "SEA",
    RAIL = "RAIL",
    SEA_RAIL = "SEA_RAIL",
    TRUCK = "TRUCK",
}

export interface IDrop {
    price: number;
    currency: string;
    conversation_percents: number;
}

interface ISegment {
    company: string;
    type: RouteType;

    effectiveFrom: string;
    effectiveTo: string;

    startPointName: string;
    startPointCountry: string;
    endPointName: string;
    endPointCountry: string;

    container_owner: string;
    container_transfer_terms: string;
    container_shipment_terms: string;

    comment?: string;
    timetable?: string;
}

export interface IMultiPriceSegment extends ISegment {
    prices: IPrice[];
}

export interface ISinglePriceSegment extends ISegment {
    beginCond?: string;
    finishCond?: string;
    container: IContainer;
    price: number;
    currency: string;
}

export interface IPrice {
    conversation_percents: number;
    currency: string;
    value: number;
    container: IContainer;
}

export interface IContainer {
    name: string;
    size: number;
    type: "HC" | "DC";
    weight_from: number;
    weight_to: number;
}
