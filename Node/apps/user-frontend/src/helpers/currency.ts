export const getCurrencySymbol = (currency: string): string | undefined => (
    { RUB: "₽", RUR: "₽", USD: "$", EUR: "€", CNY: "¥", "РУБ": "₽" }[currency.toUpperCase()]
);
