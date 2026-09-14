import { z } from "zod";

export const STRATEGIES = [
  "btl",
  "hmo",
  "flip",
  "brr",
  "development",
  "commercial",
  "rent_to_rent",
  "other",
];

export const STRATEGY_LABELS = {
  btl: "Buy-to-let",
  hmo: "HMO",
  flip: "Flip / refurb & sell",
  brr: "Buy, refurbish, refinance",
  development: "Development / conversion",
  commercial: "Commercial",
  rent_to_rent: "Rent-to-rent / lease option",
  other: "Other",
};

const money = z
  .number()
  .nullable()
  .describe("GBP in whole pounds. null if not stated anywhere in the deal sheet.");

const score10 = z.number().describe("Integer 1-10");

export const DealExtraction = z.object({
  headline: z
    .string()
    .describe("One line: what the deal is, e.g. '3-bed terrace BRR, Bolton, £95k'"),
  summary: z
    .string()
    .describe("3-5 sentence plain-English summary of the deal exactly as presented by the sourcer"),
  strategy: z
    .enum(STRATEGIES)
    .describe("The investment strategy the deal is being pitched as (or best fits)"),
  strategy_rationale: z.string().describe("One sentence on why that strategy"),
  property: z.object({
    address: z.string().nullable(),
    postcode: z.string().nullable(),
    town: z.string().nullable(),
    property_type: z
      .string()
      .nullable()
      .describe("e.g. terraced house, semi, flat, HMO, commercial unit, land"),
    bedrooms: z.number().nullable(),
    bathrooms: z.number().nullable(),
    tenure: z.enum(["freehold", "leasehold", "share_of_freehold", "unknown"]),
    lease_years_remaining: z.number().nullable(),
    epc_rating: z.string().nullable(),
    floor_area_sqm: z.number().nullable(),
    condition: z
      .string()
      .nullable()
      .describe("Condition as described, including any works needed"),
    current_occupancy: z
      .string()
      .nullable()
      .describe("Vacant, tenanted (rent & term), owner-occupied, etc."),
  }),
  financials: z.object({
    asking_price: money,
    purchase_price: money.describe(
      "Agreed or proposed purchase price. null if only an asking price is given."
    ),
    estimated_market_value: money.describe("Current market value as claimed by the sourcer"),
    refurb_cost: money.describe("Total works budget as claimed"),
    other_purchase_costs: money.describe(
      "Legal, survey, SDLT, finance fees etc if the sheet states them (exclude the sourcing fee)"
    ),
    sourcing_fee: money,
    end_value: money.describe("GDV / post-works value / refinance value as claimed"),
    monthly_rent: money.describe("Total monthly rent (sum of all rooms/units)"),
    number_of_lettable_units: z
      .number()
      .nullable()
      .describe("Rooms for an HMO, units for a block, else null"),
    monthly_service_charge_and_ground_rent: money,
    exit_strategy: z.string().nullable(),
    comparables_provided: z
      .boolean()
      .describe("true if the sheet includes sold/rental comparables with addresses or links"),
  }),
  source: z.object({
    name: z.string().nullable(),
    company: z.string().nullable(),
    contact: z.string().nullable(),
    deadline_or_urgency: z.string().nullable(),
  }),
  qualitative: z.object({
    location_demand: score10.describe(
      "1-10: rental and resale demand for this property type in this location"
    ),
    condition_risk: score10.describe(
      "1 = turnkey, 10 = structural or unknown works with no survey"
    ),
    vendor_motivation: score10.describe("1-10: how motivated or flexible the vendor appears"),
    exit_liquidity: score10.describe("1-10: how easy it would be to sell or refinance out"),
    planning_risk: score10.describe(
      "1 = no planning, licensing or change of use needed; 10 = major planning risk"
    ),
    info_completeness: score10.describe(
      "1-10: how complete and verifiable the deal sheet is (comps, photos, floor plan, costs breakdown)"
    ),
    numbers_credibility: score10.describe(
      "1-10: do the sourcer's values, rents and refurb costs look realistic for the evidence given"
    ),
    notes: z.string().describe("Short justification for the qualitative scores above"),
  }),
  red_flags: z.array(z.string()).describe("Specific concerns, each one sentence"),
  missing_information: z
    .array(z.string())
    .describe("Things an investor would need before committing that the sheet does not give"),
  questions_for_sourcer: z
    .array(z.string())
    .describe("Direct questions to send back to the person who sent the deal"),
  verdict: z
    .string()
    .describe("2-4 sentence professional opinion for the investor, in plain UK English"),
});
