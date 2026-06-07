import { PrismaClient } from "@prisma/client";
import { scoreLead } from "../src/lib/scoring";

const prisma = new PrismaClient();

type Seed = {
  name: string;
  email: string;
  phone?: string;
  company?: string;
  source: string;
  fundsAvailable?: number;
  timeframe?: string;
  chargeType?: string;
  targetReturnPct?: number;
  experience?: string;
  notes?: string;
  stage: string;
  ownerName?: string;
};

const LEADS: Seed[] = [
  {
    name: "Priya Sharma",
    email: "priya.sharma@gmail.com",
    phone: "+44 7700 900123",
    source: "WEBSITE",
    fundsAvailable: 250000,
    timeframe: "IMMEDIATE",
    chargeType: "FLEXIBLE",
    targetReturnPct: 8,
    experience: "EXPERIENCED",
    notes: "Sold a BTL portfolio, cash ready. Open to first/second charge or JV.",
    stage: "QUALIFIED",
    ownerName: "Martin",
  },
  {
    name: "David Okafor",
    email: "d.okafor@outlook.com",
    phone: "+44 7700 900456",
    company: "Okafor Holdings Ltd",
    source: "REFERRAL",
    fundsAvailable: 180000,
    timeframe: "M3",
    chargeType: "FIRST",
    targetReturnPct: 10,
    experience: "SOME",
    notes: "Referred by Priya. Wants security via first charge only.",
    stage: "OFFER",
    ownerName: "Martin",
  },
  {
    name: "Helen Whitfield",
    email: "helen.whitfield@btinternet.com",
    phone: "+44 7700 900789",
    source: "SOCIAL",
    fundsAvailable: 75000,
    timeframe: "M6",
    chargeType: "SECOND",
    targetReturnPct: 12,
    experience: "NONE",
    notes: "Came in via LinkedIn post. New to property investing, cautious.",
    stage: "CONTACTED",
  },
  {
    name: "James Crawford",
    email: "james@crawfordcapital.co.uk",
    phone: "+44 7700 900222",
    company: "Crawford Capital",
    source: "WEBSITE",
    fundsAvailable: 500000,
    timeframe: "IMMEDIATE",
    chargeType: "FLEXIBLE",
    targetReturnPct: 9,
    experience: "EXPERIENCED",
    notes: "HNW investor, multiple deals before. Wants pipeline of lease-option deals.",
    stage: "COMMITTED",
    ownerName: "Martin",
  },
  {
    name: "Aisha Rahman",
    email: "aisha.rahman@gmail.com",
    source: "CHATBOT",
    fundsAvailable: 40000,
    timeframe: "M12",
    chargeType: "SECOND",
    targetReturnPct: 15,
    experience: "NONE",
    notes: "Chatbot capture. Still saving, exploring options.",
    stage: "NEW",
  },
  {
    name: "Robert Naismith",
    email: "rob.naismith@hotmail.com",
    phone: "+44 7700 900333",
    source: "EVENT",
    fundsAvailable: 120000,
    timeframe: "M3",
    chargeType: "FIRST",
    targetReturnPct: 11,
    experience: "SOME",
    notes: "Met at Manchester property meetup. Pension-led cash.",
    stage: "QUALIFYING",
    ownerName: "Martin",
  },
  {
    name: "Sophie Bennett",
    email: "sophie.bennett@gmail.com",
    source: "WEBSITE",
    fundsAvailable: 22000,
    timeframe: "UNKNOWN",
    chargeType: "EQUITY",
    targetReturnPct: 25,
    experience: "NONE",
    notes: "Unrealistic return expectation, small pot. Nurture only.",
    stage: "NEW",
  },
  {
    name: "Marcus Lindholm",
    email: "marcus@lindholm-invest.com",
    phone: "+44 7700 900444",
    company: "Lindholm Invest",
    source: "REFERRAL",
    fundsAvailable: 350000,
    timeframe: "IMMEDIATE",
    chargeType: "FLEXIBLE",
    targetReturnPct: 8,
    experience: "EXPERIENCED",
    notes: "Family office introduction. Deploying across several deals this year.",
    stage: "INVESTED",
    ownerName: "Martin",
  },
  {
    name: "Grace Adeyemi",
    email: "grace.adeyemi@yahoo.co.uk",
    source: "SOCIAL",
    fundsAvailable: 60000,
    timeframe: "M6",
    chargeType: "SECOND",
    targetReturnPct: 13,
    experience: "SOME",
    stage: "QUALIFYING",
  },
  {
    name: "Tom Beckett",
    email: "tom.beckett@gmail.com",
    source: "WEBSITE",
    fundsAvailable: 15000,
    timeframe: "M12",
    chargeType: "FIRST",
    targetReturnPct: 20,
    experience: "NONE",
    notes: "Low funds, high expectations. Likely a long-term nurture.",
    stage: "LOST",
  },
  {
    name: "Eleanor Voss",
    email: "eleanor.voss@protonmail.com",
    phone: "+44 7700 900555",
    source: "REFERRAL",
    fundsAvailable: 200000,
    timeframe: "M3",
    chargeType: "FLEXIBLE",
    targetReturnPct: 9,
    experience: "EXPERIENCED",
    stage: "QUALIFIED",
    ownerName: "Martin",
  },
  {
    name: "Daniel Hughes",
    email: "dan.hughes@gmail.com",
    source: "CHATBOT",
    fundsAvailable: 90000,
    timeframe: "M6",
    chargeType: "SECOND",
    targetReturnPct: 12,
    experience: "SOME",
    notes: "Chatbot lead, asked about payment agreements specifically.",
    stage: "CONTACTED",
  },
];

async function main() {
  console.log("Resetting investor leads…");
  await prisma.activity.deleteMany();
  await prisma.investorLead.deleteMany();

  let i = 0;
  for (const lead of LEADS) {
    const { score, band } = scoreLead(lead);
    const created = await prisma.investorLead.create({
      data: {
        ...lead,
        score,
        scoreBand: band,
        position: i++,
        activities: {
          create: [
            {
              type: "CREATED",
              summary: `Lead captured from ${lead.source.toLowerCase()}`,
              actor: "system",
            },
            {
              type: "SCORE",
              summary: `Scored ${score}/100 (${band})`,
              actor: "system",
            },
          ],
        },
      },
    });
    console.log(`  + ${created.name} — ${score} (${band}) — ${created.stage}`);
  }

  console.log(`\nSeeded ${LEADS.length} investor leads.`);
}

main()
  .catch((e) => {
    console.error(e);
    process.exit(1);
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
