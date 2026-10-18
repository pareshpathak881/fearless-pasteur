"""Market projection calculator tool for Project Atlas.

Computes CAGR projections, regional shares, and multi-year market estimates.
Enforces explicit disclosure of formulas, mathematical assumptions,
base-year ambiguities, and labels figures as derived estimates rather than quoted facts.
"""

from typing import Dict, Any, Optional


class MarketCalculator:
    @staticmethod
    def project_cagr(
        start_value: float,
        cagr_percent: float,
        start_year: int,
        target_year: int,
        is_base_year_included: bool = True
    ) -> Dict[str, Any]:
        """Compute compound annual growth rate projection.
        
        Formula: V_target = V_start * (1 + r)^n
        """
        r = cagr_percent / 100.0
        n_periods = target_year - start_year
        
        # Calculate primary projection
        projected_value = start_value * ((1.0 + r) ** n_periods)
        
        # Calculate alternative projection if base year interpretation varies by 1 year
        alt_n_periods = n_periods - 1 if n_periods > 1 else n_periods
        alt_projected_value = start_value * ((1.0 + r) ** alt_n_periods)

        return {
            "type": "cagr_projection",
            "is_derived": True,
            "label": "Derived Estimate (Not a Quoted Fact)",
            "start_year": start_year,
            "target_year": target_year,
            "start_value": start_value,
            "cagr_percent": cagr_percent,
            "n_periods": n_periods,
            "projected_value": round(projected_value, 2),
            "alt_projected_value_5yr": round(alt_projected_value, 2),
            "formula": f"V_{{{target_year}}} = V_{{{start_year}}} * (1 + {cagr_percent}%)^{{{n_periods}}}",
            "assumptions": [
                f"Constant compound annual growth rate of {cagr_percent}% holds annually through {target_year}.",
                f"Baseline {start_year} valuation of USD {start_value}B.",
                "Macroeconomic conditions, public utility budgets, and regulatory conservation mandates remain steady."
            ],
            "ambiguity_notes": (
                f"Base-year timing ambiguity: The forecast window is stated as 2025–2030 from a 2024 base. "
                f"Applying n={n_periods} compounding cycles yields USD {round(projected_value, 2)}B; "
                f"if assuming 5 discrete annual increments (2025 as year 1), the result is USD {round(alt_projected_value, 2)}B."
            )
        }

    @staticmethod
    def calculate_regional_share(
        global_value: float,
        share_percent: float,
        region: str,
        year: int,
        source_report: str
    ) -> Dict[str, Any]:
        """Compute regional segment sizing from global total."""
        derived_val = global_value * (share_percent / 100.0)
        return {
            "type": "regional_share_projection",
            "is_derived": True,
            "label": "Derived Estimate (Not a Quoted Fact)",
            "region": region,
            "year": year,
            "share_percent": share_percent,
            "derived_value": round(derived_val, 2),
            "formula": f"{region}_{{{year}}} = Global_{{{year}}} * ({share_percent} / 100)",
            "assumptions": [
                f"Assumes {region} retains its {share_percent}% global market share through {year}.",
                f"Based on baseline figures established in {source_report}."
            ],
            "ambiguity_notes": (
                f"Regional share dynamics: While {source_report} records {region} at {share_percent}% in 2024, "
                f"regional growth rates may diverge from the global CAGR, causing the actual {year} regional share to fluctuate."
            )
        }


calculator = MarketCalculator()
