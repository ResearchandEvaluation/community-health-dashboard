# One-time setup

Four steps. Steps 1 and 2 take about 15 minutes. Step 3 is for whoever manages the PHIL website.

## 1. Create the GitHub account and repository

1. Go to https://github.com/signup and create an account for PHIL (use a shared PHIL mailbox, not a
   personal one, so the account outlives any one person). Turn on two-factor authentication.
2. Create a new repository named `community-health-dashboard`, set to **Public** (GitHub Pages on a
   free account requires a public repository; the code and data are all public data anyway).
3. Upload this folder's contents to the repository. Easiest route: on the repository page choose
   **Add file > Upload files** and drag the whole folder in, or ask Claude to push it once you give it
   access (Settings > Collaborators, or a fine-grained access token with Contents and Pages permissions).

## 2. Turn on the automated refresh

1. **Secrets:** Settings > Secrets and variables > Actions > New repository secret.
   Name `CENSUS_API_KEY`, value: the Census key (sign up free at https://api.census.gov/data/key_signup.html).
2. **Pages:** Settings > Pages > Build and deployment > Source: **GitHub Actions**.
3. **First run:** Actions tab > "Refresh data and publish dashboard" > Run workflow. It takes about
   10 minutes. When it finishes, the page is live at `https://<account>.github.io/community-health-dashboard/`.
4. **Notifications:** the account's email receives a message when a run fails. Nothing is published
   from a failed run; the previous version stays live.

## 3. Point the subdomain at the page (website manager, GoDaddy)

PHIL's domain DNS is managed in GoDaddy. Have the person who holds the GoDaddy login present: if the
domain has Domain Protection, GoDaddy asks for a 2-step verification code or a one-time password sent
to the GoDaddy account email before it saves a change.

1. Sign in to GoDaddy and open the **Domain Portfolio**.
2. Select **pophealthinnovationlab.org** to open its Domain Settings page, then select the **DNS** tab.
3. Check the list for an existing record named `dashboard`. If one exists, edit it instead of adding a new one.
4. Select **Add New Record** and set:
   * **Type:** CNAME
   * **Name:** `dashboard` (the prefix only, without `.pophealthinnovationlab.org`)
   * **Value:** `<account>.github.io` (the GitHub account name followed by `.github.io`, with no `https://` and no repository name)
   * **TTL:** leave the default (1 hour)
5. Select **Save**. Most changes take effect within an hour; full propagation can take up to 48 hours.
6. In the GitHub repository: Settings > Pages > Custom domain, enter `dashboard.pophealthinnovationlab.org`,
   save, and tick **Enforce HTTPS** once the DNS check passes (a few minutes to an hour).
7. On the WordPress site, add a menu item linking to https://dashboard.pophealthinnovationlab.org
   (for example under Resources).

GoDaddy's own instructions: https://www.godaddy.com/help/add-a-cname-record-19236

The file `site/CNAME` already contains the subdomain, so each publish keeps the custom domain.

## 4. After the first live publish

* Remove the "Prototype for Team Review" label: delete that line in `site/template.html`.
* Share the Resources page process with the communications team: edits to `data/manual/resources.json`
  go live on the next rebuild (within minutes of the commit, or Monday at the latest).

## Where things can break, and what to do

| Symptom | Likely cause | Fix |
|---|---|---|
| Refresh fails on `acs` | Census key missing or expired | Check the `CENSUS_API_KEY` secret |
| Refresh fails on `cde` | CDE posted the new school year under a new file name | Add it to `scripts/cde.py` |
| Refresh fails on `places` or `cvd_mortality` | CDC published a new release with a new dataset id | Update the id at the top of the script |
| Check fails with "period went backwards" | A source changed its data layout | Open the script's output in the Actions log |
