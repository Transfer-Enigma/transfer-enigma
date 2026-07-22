import type { IdIsExternal } from "@/interfaces/Point";

export interface ICalculatorReadyToSendPayload {
    dispatchDate?: string;
    departureInternalIds: number[];
    destinationInternalIds: number[];
    departureExternalIds: string[];
    destinationExternalIds: string[];
    containerType?: string;
    cargoWeight?: number;
    currency: string;
    truckStartPointId?: string;
    truckEndPointId?: string;
}

export interface ICalculatorPayload {
    date?: string;
    departureIds?: IdIsExternal[];
    destinationIds?: IdIsExternal[];
    containerType?: string;
    containerWeight?: number;
    truckStartIds?: IdIsExternal[];
    truckEndIds?: IdIsExternal[];
}

export interface ICalculatorPayloadWithCurrency extends ICalculatorPayload {
    currency?: string;
}
