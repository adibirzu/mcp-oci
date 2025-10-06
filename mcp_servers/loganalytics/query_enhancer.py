#!/usr/bin/env python3
"""
OCI Log Analytics Query Enhancer

This module provides query transformation, field mapping, and validation
for OCI Log Analytics queries to handle common field naming issues and
improve query syntax compatibility.
"""

import re
import json
from typing import Dict, List, Tuple, Optional, Set
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass
class FieldMapping:
    """Field mapping configuration"""
    source_field: str
    target_field: str
    data_type: str
    description: str
    aliases: List[str] = None

    def __post_init__(self):
        if self.aliases is None:
            self.aliases = []


@dataclass
class QueryValidationResult:
    """Result of query validation"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    suggestions: List[str]
    transformed_query: Optional[str] = None


class LogAnalyticsFieldMapper:
    """Maps common field names to OCI Log Analytics schema"""

    def __init__(self):
        self.field_mappings = self._build_field_mappings()
        self.field_aliases = self._build_field_aliases()
        self.reserved_functions = self._build_reserved_functions()

    def _build_field_mappings(self) -> Dict[str, FieldMapping]:
        """Build comprehensive field mappings for common scenarios"""
        mappings = {}

        # Cost and Billing Fields (AWS -> OCI mapping)
        cost_fields = [
            FieldMapping("lineItem_intervalUsageEnd", "Usage End Time", "datetime",
                        "End time of usage interval", ["usage_end", "interval_end", "usage_time"]),
            FieldMapping("lineItem_intervalUsageStart", "Usage Start Time", "datetime",
                        "Start time of usage interval", ["usage_start", "interval_start"]),
            FieldMapping("lineItem_usageAmount", "Usage Amount", "number",
                        "Amount of usage", ["usage_amount", "quantity", "usage_qty"]),
            FieldMapping("lineItem_blendedCost", "Cost", "number",
                        "Blended cost", ["cost", "amount", "charge"]),
            FieldMapping("product_serviceName", "Service Name", "string",
                        "Name of the service", ["service", "product", "service_name"]),
            FieldMapping("product_compartmentName", "Compartment Name", "string",
                        "Compartment name", ["compartment", "compartment_name"]),
            FieldMapping("product_Description", "Product Description", "string",
                        "Product description", ["description", "product_desc", "service_desc"]),
            FieldMapping("usage_billedQuantity2", "Billed Quantity", "number",
                        "Billed quantity", ["billed_qty", "billed_amount", "quantity"]),
            FieldMapping("usage_billedQuantityOverage", "Overage Amount", "number",
                        "Overage billing amount", ["overage", "overage_cost", "excess_cost"]),
        ]

        for mapping in cost_fields:
            mappings[mapping.source_field] = mapping
            # Also map aliases
            for alias in mapping.aliases:
                mappings[alias] = mapping

        # OCI Log Analytics standard fields
        oci_fields = [
            FieldMapping("'Log Source'", "Log Source", "string",
                        "Source of the log data", ["log_source", "source"]),
            FieldMapping("'Defined Tags'", "Defined Tags", "string",
                        "OCI defined tags", ["defined_tags", "tags"]),
            FieldMapping("'Freeform Tags'", "Freeform Tags", "string",
                        "OCI freeform tags", ["freeform_tags", "free_tags"]),
            FieldMapping("'Oracle Compartment ID'", "Compartment ID", "string",
                        "OCI compartment identifier", ["compartment_id", "comp_id"]),
            FieldMapping("'Oracle Compartment Name'", "Compartment Name", "string",
                        "OCI compartment name", ["compartment_name", "comp_name"]),
            FieldMapping("'Oracle Tenancy ID'", "Tenancy ID", "string",
                        "OCI tenancy identifier", ["tenancy_id"]),
        ]

        for mapping in oci_fields:
            mappings[mapping.source_field] = mapping
            for alias in mapping.aliases:
                mappings[alias] = mapping

        return mappings

    def _build_field_aliases(self) -> Dict[str, str]:
        """Build reverse mapping from common aliases to OCI fields"""
        aliases = {}
        for source_field, mapping in self.field_mappings.items():
            # Map all aliases to the target field
            for alias in mapping.aliases:
                aliases[alias.lower()] = mapping.target_field
            aliases[source_field.lower()] = mapping.target_field
        return aliases

    def _build_reserved_functions(self) -> Set[str]:
        """OCI Log Analytics reserved functions and operators"""
        return {
            'stats', 'sum', 'avg', 'count', 'min', 'max', 'stddev',
            'sort', 'head', 'tail', 'where', 'search', 'eval', 'fields',
            'dedup', 'rare', 'top', 'chart', 'timechart', 'bucket',
            'by', 'as', 'and', 'or', 'not', 'in', 'like', 'regex',
            'earliest', 'latest', 'now', 'strftime', 'strptime',
        }


class LogAnalyticsQueryEnhancer:
    """Enhanced query processor for OCI Log Analytics"""

    def __init__(self):
        self.field_mapper = LogAnalyticsFieldMapper()

    def validate_and_transform_query(self, query: str) -> QueryValidationResult:
        """Validate and transform a Log Analytics query"""
        errors = []
        warnings = []
        suggestions = []

        # Start with the original query
        transformed_query = query.strip()

        # 1. Check for common field mapping issues
        field_issues = self._check_field_mappings(transformed_query)
        if field_issues:
            errors.extend(field_issues['errors'])
            warnings.extend(field_issues['warnings'])
            suggestions.extend(field_issues['suggestions'])
            if field_issues.get('transformed_query'):
                transformed_query = field_issues['transformed_query']

        # 2. Validate query syntax
        syntax_issues = self._validate_syntax(transformed_query)
        if syntax_issues:
            errors.extend(syntax_issues['errors'])
            warnings.extend(syntax_issues['warnings'])
            suggestions.extend(syntax_issues['suggestions'])

        # 3. Check time-based operations
        time_issues = self._validate_time_operations(transformed_query)
        if time_issues:
            errors.extend(time_issues['errors'])
            warnings.extend(time_issues['warnings'])
            suggestions.extend(time_issues['suggestions'])

        # 4. Optimize aggregations
        optimized = self._optimize_aggregations(transformed_query)
        if optimized != transformed_query:
            transformed_query = optimized
            suggestions.append("Query optimized for better performance")

        return QueryValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions,
            transformed_query=transformed_query if transformed_query != query else None
        )

    def _check_field_mappings(self, query: str) -> Dict:
        """Check and fix field mapping issues"""
        errors = []
        warnings = []
        suggestions = []
        transformed_query = query

        # Find field references in the query
        field_patterns = [
            r'\b([a-zA-Z_][a-zA-Z0-9_]*)\s*=',  # field = value
            r'by\s+([a-zA-Z_][a-zA-Z0-9_]*)',   # by field
            r'sum\(([^)]+)\)',                   # sum(field)
            r'avg\(([^)]+)\)',                   # avg(field)
            r'count\(([^)]+)\)',                 # count(field)
            r'stats\s+[^|]*\s+by\s+([^|]+)',    # stats ... by field
        ]

        found_fields = set()
        for pattern in field_patterns:
            matches = re.finditer(pattern, query, re.IGNORECASE)
            for match in matches:
                field = match.group(1).strip()
                found_fields.add(field)

        # Check each found field
        for field in found_fields:
            if field in self.field_mapper.field_mappings:
                mapping = self.field_mapper.field_mappings[field]
                if mapping.source_field != mapping.target_field:
                    # This field needs mapping
                    # For OCI Log Analytics, we need to use proper field names
                    suggested_field = self._get_oci_field_name(field)
                    if suggested_field != field:
                        errors.append(f"Invalid field for BY: {field}. Use '{suggested_field}' instead.")
                        suggestions.append(f"Replace '{field}' with '{suggested_field}'")
                        # Transform the query
                        # Avoid double quotes by checking if already quoted
                        replacement = suggested_field if suggested_field.startswith("'") else f"'{suggested_field}'"
                        transformed_query = re.sub(
                            rf'\b{re.escape(field)}\b',
                            replacement,
                            transformed_query
                        )
            else:
                # Unknown field, try to suggest alternatives
                suggestions.append(f"Unknown field '{field}'. Consider using standard OCI Log Analytics fields.")

        return {
            'errors': errors,
            'warnings': warnings,
            'suggestions': suggestions,
            'transformed_query': transformed_query if transformed_query != query else None
        }

    def _get_oci_field_name(self, field: str) -> str:
        """Get the appropriate OCI Log Analytics field name"""
        field_lower = field.lower()

        # Map common cost/billing fields to OCI equivalents
        # Based on OCI Log Analytics schema for cost/usage data
        mapping_rules = {
            'lineitem_intervalusageend': "'Log Date'",
            'lineitem_intervalusagestart': "'Log Date'",
            'lineitem_usageamount': "'Usage Quantity'",
            'lineitem_blendedcost': "'Cost'",
            'product_servicename': "'Service Name'",
            'product_compartmentname': "'Compartment Name'",
            'product_description': "'Product Description'",
            'usage_billedquantity2': "'Usage Quantity'",
            'usage_billedquantityoverage': "'Overage Amount'",
        }

        if field_lower in mapping_rules:
            return mapping_rules[field_lower]

        # If no specific mapping, try to make it a quoted field
        if not field.startswith("'") and not field.endswith("'"):
            return f"'{field}'"

        return field

    def _validate_syntax(self, query: str) -> Dict:
        """Validate Log Analytics query syntax"""
        errors = []
        warnings = []
        suggestions = []

        # Check for basic syntax issues
        if '|' not in query:
            warnings.append("Query may benefit from using pipe operators for better structure")

        # Check for stats operations without proper BY clause
        if 'stats' in query.lower():
            if 'by' not in query.lower():
                warnings.append("Stats operation without BY clause may not aggregate correctly")
            else:
                # Validate BY fields are properly quoted
                by_match = re.search(r'by\s+([^|]+)', query, re.IGNORECASE)
                if by_match:
                    by_fields = by_match.group(1).strip()
                    # Check if fields contain spaces but aren't quoted
                    fields = [f.strip() for f in by_fields.split(',')]
                    for field in fields:
                        if ' ' in field and not (field.startswith("'") and field.endswith("'")):
                            errors.append(f"Field with spaces must be quoted: {field}")
                            suggestions.append(f"Use '{field}' instead of {field}")

        return {
            'errors': errors,
            'warnings': warnings,
            'suggestions': suggestions
        }

    def _validate_time_operations(self, query: str) -> Dict:
        """Validate time-based operations"""
        errors = []
        warnings = []
        suggestions = []

        # Look for time field usage
        time_patterns = [
            r'lineItem_intervalUsageEnd',
            r'usage.*End',
            r'interval.*End',
            r'time.*end',
        ]

        for pattern in time_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                suggestions.append("For time-based grouping, consider using 'Log Date' or time bucket functions")
                break

        return {
            'errors': errors,
            'warnings': warnings,
            'suggestions': suggestions
        }

    def _optimize_aggregations(self, query: str) -> str:
        """Optimize aggregation queries for better performance"""
        optimized = query

        # Convert multiple sum operations to single stats command
        sum_pattern = r'sum\(([^)]+)\)\s*as\s*([^,|]+)'
        matches = re.findall(sum_pattern, optimized, re.IGNORECASE)

        if len(matches) > 1:
            # Multiple sum operations found, could be optimized
            pass  # Keep original for now, could add optimization logic here

        return optimized

    def get_field_suggestions(self, partial_field: str) -> List[str]:
        """Get field name suggestions based on partial input"""
        partial_lower = partial_field.lower()
        suggestions = []

        for field, mapping in self.field_mapper.field_mappings.items():
            if partial_lower in field.lower():
                suggestions.append(mapping.target_field)
            for alias in mapping.aliases:
                if partial_lower in alias.lower():
                    suggestions.append(mapping.target_field)

        return list(set(suggestions))[:10]  # Return top 10 unique suggestions


def enhance_log_analytics_query(query: str) -> Dict:
    """Main function to enhance a Log Analytics query"""
    enhancer = LogAnalyticsQueryEnhancer()
    result = enhancer.validate_and_transform_query(query)

    return {
        'original_query': query,
        'is_valid': result.is_valid,
        'errors': result.errors,
        'warnings': result.warnings,
        'suggestions': result.suggestions,
        'enhanced_query': result.transformed_query or query,
        'timestamp': datetime.utcnow().isoformat()
    }


if __name__ == "__main__":
    # Example usage
    test_query = "'Log Source' = 'VF_budget_noFocus' and product_Description = 'database exadata - additional ocpus - byol' and product_compartmentName = 'drcc-vf-it-shared-exacs' | stats sum(usage_billedQuantity2) as daily_usage, sum(usage_billedQuantityOverage) as daily_cost by lineItem_intervalUsageEnd | sort lineItem_intervalUsageEnd"

    result = enhance_log_analytics_query(test_query)
    print(json.dumps(result, indent=2))