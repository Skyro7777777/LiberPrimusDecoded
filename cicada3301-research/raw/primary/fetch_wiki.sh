#!/usr/bin/env bash
# Fetch all primary-source URLs in parallel batches.
set -e
cd /home/z/my-project/cicada3301-research/raw/primary

# Helper: fetch one URL if not already fetched
fetch() {
  local name="$1"
  local url="$2"
  if [ -f "${name}.json" ] && [ -s "${name}.json" ]; then
    echo "skip ${name} (exists)"
    return
  fi
  z-ai function -n page_reader -a "{\"url\": \"${url}\"}" -o "${name}.json" >/dev/null 2>&1 && \
    echo "ok ${name}" || echo "FAIL ${name}"
}

export -f fetch

# Batch 1: Uncovering Cicada wiki pages (14)
fetch primary_2013_p1 "https://uncovering-cicada.fandom.com/wiki/What_Happened_Part_1_(2013)" &
fetch primary_2013_p2 "https://uncovering-cicada.fandom.com/wiki/What_Happened_Part_2_(2013)" &
fetch primary_2014     "https://uncovering-cicada.fandom.com/wiki/What_Happened_(2014)" &
wait
echo "Batch 1a done"

fetch primary_lp_post2014 "https://uncovering-cicada.fandom.com/wiki/What_Happened_Liber_Primus_(Post_2014)" &
fetch primary_lp_main      "https://uncovering-cicada.fandom.com/wiki/Liber_Primus" &
fetch primary_freq_analysis "https://uncovering-cicada.fandom.com/wiki/Frequency_Analysis_Unsolved_Pages" &
fetch primary_unused_hints "https://uncovering-cicada.fandom.com/wiki/Possible_hints_never_used" &
wait
echo "Batch 1b done"

fetch primary_references "https://uncovering-cicada.fandom.com/wiki/List_of_all_Cicada%27s_references" &
fetch primary_outguess    "https://uncovering-cicada.fandom.com/wiki/OutGuess" &
fetch primary_page56      "https://uncovering-cicada.fandom.com/wiki/PAGE_56" &
fetch primary_page57      "https://uncovering-cicada.fandom.com/wiki/PAGE_57" &
wait
echo "Batch 1c done"

fetch primary_unsolved    "https://uncovering-cicada.fandom.com/wiki/Liber_Primus_Unsolved_Pages" &
fetch primary_updates2025 "https://uncovering-cicada.fandom.com/wiki/Liber_Primus_Updates_2025" &
wait
echo "Batch 1d done"

echo "ALL WIKI FETCHES COMPLETE"
ls -la *.json
