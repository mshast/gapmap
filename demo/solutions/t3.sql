WITH refund_totals AS (
  SELECT order_id, SUM(amount_cents) AS refunded
  FROM refunds
  GROUP BY order_id
)
SELECT COALESCE(NULLIF(c.region, ''), 'Unknown') AS region,
       SUM(o.amount_cents - COALESCE(r.refunded, 0)) AS net_revenue_cents
FROM orders o
JOIN customers c ON c.id = o.customer_id
LEFT JOIN refund_totals r ON r.order_id = o.id
WHERE o.status = 'completed'
GROUP BY 1
ORDER BY 1;
