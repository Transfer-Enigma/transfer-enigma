-- Synthetic E2E seed (workflow #1). No real data, no secrets.
-- Minimal graph: 3 points, 2 companies, 2 containers, 3 direct RAIL segments.
-- Effective range 2024-01-01..2030-12-31 covers any dispatchDate used by tests.
-- Idempotent: safe to apply multiple times.

INSERT INTO companies (id, name) VALUES
  (1, 'E2E Rail Line'),
  (2, 'E2E Sea Line')
ON DUPLICATE KEY UPDATE name = VALUES(name);

INSERT INTO points (id, city, country, RU_city, RU_country) VALUES
  (1, 'E2E Alpha', 'EA', 'Е2Е Альфа', 'ЕА'),
  (2, 'E2E Beta', 'EB', 'Е2Е Бета', 'ЕБ'),
  (3, 'E2E Gamma', 'EG', 'Е2Е Гамма', 'ЕГ')
ON DUPLICATE KEY UPDATE city = VALUES(city), country = VALUES(country);

INSERT INTO containers (id, size, weight_from, weight_to, name, type) VALUES
  (1, 20, 0, 28000, '20DC', 'DC'),
  (2, 40, 0, 28000, '40HC', 'HC')
ON DUPLICATE KEY UPDATE name = VALUES(name);

INSERT INTO routes
  (id, company_id, start_point_id, end_point_id, dropp_off_point_id,
   effective_from, effective_to, comment, timetable, is_through,
   type, container_transfer_terms, container_shipment_terms, container_owner) VALUES
  (1, 1, 1, 2, NULL, '2024-01-01 00:00:00', '2030-12-31 00:00:00',
   'E2E seed Alpha-Beta', NULL, 0, 'RAIL', 'FIFO', 'FOB', 'COC'),
  (2, 1, 1, 3, NULL, '2024-01-01 00:00:00', '2030-12-31 00:00:00',
   'E2E seed Alpha-Gamma', NULL, 0, 'RAIL', 'FIFO', 'FOB', 'COC'),
  (3, 2, 2, 3, NULL, '2024-01-01 00:00:00', '2030-12-31 00:00:00',
   'E2E seed Beta-Gamma', NULL, 0, 'RAIL', 'FIFO', 'FOB', 'COC')
ON DUPLICATE KEY UPDATE comment = VALUES(comment);

INSERT INTO prices (id, route_id, container_id, value, currency, conversation_percents) VALUES
  (1, 1, 1, 1500.0, 'USD', 0),
  (2, 2, 1, 2500.0, 'USD', 0),
  (3, 3, 1, 1200.0, 'USD', 0),
  (4, 1, 2, 2200.0, 'USD', 0)
ON DUPLICATE KEY UPDATE value = VALUES(value), currency = VALUES(currency);
