"""NTEE code filters and veteran keyword lists for organization identification."""

# Primary NTEE codes for veteran/military organizations
# W = Public, Society Benefit – Military/Veterans' Organizations
VETERAN_NTEE_CODES = {
    "W": "Public, Society Benefit - Military/Veterans",
    "W20": "Military/Veterans Organizations",
    "W22": "Veterans Organizations - NEC",
    "W30": "Military/Veterans Organizations",
    "W40": "Veterans Service Organizations",
    "W50": "Military/Veterans - Other",
    "W60": "Servicemembers Organizations",
    "W70": "Military Family Support",
    "W80": "Veterans Housing/Shelter",
    "W99": "Military/Veterans - NEC",
}

# Broader NTEE categories that often include veteran-serving orgs
RELATED_NTEE_PREFIXES = [
    "W",    # All military/veterans
    "P70",  # Residential Care - includes veteran housing
    "L41",  # Housing for Specific Groups - veteran housing
]

# IRS subsection code for armed forces organizations
ARMED_FORCES_SUBSECTION = "19"  # 501(c)(19) — Veterans' organizations

# Keywords for name-based matching (case-insensitive)
# Applied to org names across ALL NTEE codes to catch miscategorized orgs
VETERAN_KEYWORDS = [
    "veteran",
    "veterans",
    "vets",
    "vet ",        # space-delimited to avoid matching "veterinary"
    "vfw",
    "american legion",
    "amvets",
    "dav",
    "disabled american",
    "military",
    "armed forces",
    "army",
    "navy",
    "marine",
    "marines",
    "air force",
    "coast guard",
    "national guard",
    "purple heart",
    "medal of honor",
    "gold star",
    "blue star",
    "wounded warrior",
    "fisher house",
    "uso ",
    "uso,",
    "united service organizations",
    "legion post",
    "legion aux",
    "war veteran",
    "combat veteran",
    "vietnam veteran",
    "iraq veteran",
    "afghanistan veteran",
    "korean war",
    "desert storm",
    "gulf war",
    "pow",
    "mia",
    "prisoner of war",
    "gi bill",
    "service member",
    "servicemember",
    "fallen hero",
    "fallen soldier",
    "deployment",
    "reintegration",
    "ptsd",          # common in veteran-service orgs
    "tbi",           # traumatic brain injury — veteran service context
    "mil spouse",
    "military spouse",
    "military family",
    "military families",
    "troops",
    "troop support",
    "active heroes",
    "team rubicon",
    "honor flight",
    "soldier",
    "soldiers",
    "warrior",
    "warriors",
    "heroes ",          # space-delimited: catches "heroes inc", "heroes foundation"
    "for heroes",
    "4 heroes",
    "heroic",
    "battle buddy",
    "bunker labs",
    "team red white",
    "mission 22",
    "k9s for warriors",
    "soldier ride",
    "operation homefront",
    "operation heal",
    "operation mend",
    "boots on the ground",
    "22kill",
    "stop soldier suicide",
    "headstrong",
    "code of support",
    "got your 6",
    "rally point",
    "semper fi fund",
    "bob woodruff",
    "pat tillman",
    "gary sinise",
    "hire heroes",
    "american corporate partners",
]

# Words to EXCLUDE if matched alone (reduces false positives)
EXCLUDE_PATTERNS = [
    "veterinary",
    "veterinarian",
    "vet clinic",
    "vet hospital",
    "animal vet",
    "pet vet",
    "salvation army",   # charity, not military-focused
]

# NRD service categories relevant to veterans
NRD_CATEGORIES = [
    "benefits-and-compensation",
    "education-and-training",
    "employment",
    "family-and-caregiver-support",
    "health",
    "homeless-assistance",
    "housing",
    "transportation",
    "other-services-and-resources",
]
