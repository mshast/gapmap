/**
 * Formats a SQL query with standard indentation and capitalized keywords.
 */
export function formatSql(rawSql: string): string {
  if (!rawSql || !rawSql.trim()) return rawSql;

  // 1. Extract string literals and comments to preserve them untouched
  const literals: string[] = [];
  let placeholderIndex = 0;

  // Replace single-line comments (-- ...), multi-line comments (/* ... */),
  // and string literals ('...') with placeholders
  let masked = rawSql.replace(
    /(--[^\r\n]*)|(\/\*[\s\S]*?\*\/)|('(?:''|[^'])*')/g,
    (match) => {
      const placeholder = `__GAPMAP_SQL_TOKEN_${placeholderIndex++}__`;
      literals.push(match);
      return placeholder;
    }
  );

  // 2. Normalize whitespace
  masked = masked.replace(/\r\n/g, "\n").trim();

  // 3. Keywords list for uppercase
  const KEYWORDS = [
    "SELECT", "FROM", "WHERE", "LEFT JOIN", "RIGHT JOIN", "INNER JOIN",
    "OUTER JOIN", "FULL JOIN", "CROSS JOIN", "JOIN", "ON", "AND", "OR", "GROUP BY",
    "ORDER BY", "HAVING", "LIMIT", "OFFSET", "AS", "IN", "IS", "NOT", "NULL",
    "LIKE", "ILIKE", "BETWEEN", "EXISTS", "CASE", "WHEN", "THEN", "ELSE",
    "END", "DESC", "ASC", "DISTINCT", "ALL", "UNION ALL", "UNION", "WITH",
    "INSERT INTO", "VALUES", "UPDATE", "SET", "DELETE FROM",
    "COALESCE", "COUNT", "SUM", "AVG", "MIN", "MAX", "ROUND", "CAST"
  ];

  // Capitalize known keywords (sorted by length descending so multi-word keywords match first)
  const sortedKeywords = [...KEYWORDS].sort((a, b) => b.length - a.length);
  for (const kw of sortedKeywords) {
    const regex = new RegExp(`\\b${kw.replace(/ /g, "\\s+")}\\b`, "gi");
    masked = masked.replace(regex, kw);
  }

  // 4. Break major top-level clauses onto new lines
  const MAJOR_CLAUSES = [
    "SELECT",
    "FROM",
    "LEFT JOIN",
    "RIGHT JOIN",
    "INNER JOIN",
    "OUTER JOIN",
    "FULL JOIN",
    "CROSS JOIN",
    "JOIN",
    "WHERE",
    "GROUP BY",
    "HAVING",
    "ORDER BY",
    "LIMIT",
    "OFFSET",
    "UNION ALL",
    "UNION",
  ];

  for (const clause of MAJOR_CLAUSES) {
    const clauseRegex = new RegExp(`(?<!^)\\s+(${clause})\\b`, "g");
    masked = masked.replace(clauseRegex, "\n$1");
  }

  // 5. Format clauses line by line
  const lines = masked.split("\n").map((l) => l.trim()).filter(Boolean);
  const formattedLines: string[] = [];

  let inSelect = false;

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    if (/^SELECT\b/.test(line)) {
      inSelect = true;
      const rest = line.slice("SELECT".length).trim();
      formattedLines.push("SELECT");
      if (rest) {
        const cols = splitTopLevel(rest, ",");
        for (let c = 0; c < cols.length; c++) {
          const colTrim = cols[c].trim();
          if (!colTrim) continue;
          const isLast = c === cols.length - 1;
          formattedLines.push(`  ${colTrim}${isLast ? "" : ","}`);
        }
      }
      continue;
    }

    if (MAJOR_CLAUSES.some((clause) => line.startsWith(clause))) {
      inSelect = false;
      formattedLines.push(line);
      continue;
    }

    if (inSelect) {
      const cols = splitTopLevel(line, ",");
      for (let c = 0; c < cols.length; c++) {
        const colTrim = cols[c].trim();
        if (!colTrim) continue;
        const isLast = c === cols.length - 1;
        formattedLines.push(`  ${colTrim}${isLast ? "" : ","}`);
      }
      continue;
    }

    formattedLines.push(line);
  }

  let result = formattedLines.join("\n");

  // Format AND / OR on new lines under WHERE if on the same line
  result = result.replace(/\n(WHERE\s+.*?)\s+\b(AND|OR)\b\s+/g, "\n$1\n  $2 ");

  // 6. Restore string literals and comments
  for (let i = 0; i < literals.length; i++) {
    result = result.replace(`__GAPMAP_SQL_TOKEN_${i}__`, literals[i]);
  }

  // Ensure statement ending with semicolon doesn't have extra spaces before ;
  result = result.replace(/\s+;/g, ";");

  return result.trim();
}

/**
 * Splits a string on a delimiter only at top level (not inside parentheses).
 */
function splitTopLevel(str: string, delimiter: string): string[] {
  const parts: string[] = [];
  let depth = 0;
  let current = "";

  for (let i = 0; i < str.length; i++) {
    const char = str[i];
    if (char === "(") depth++;
    else if (char === ")") depth--;

    if (char === delimiter && depth === 0) {
      parts.push(current);
      current = "";
    } else {
      current += char;
    }
  }
  if (current.trim()) {
    parts.push(current);
  }
  return parts;
}
