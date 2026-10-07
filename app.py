from flask import Flask, render_template, request, redirect, url_for, session, flash
from supabase import create_client, client 
from dotenv import load_dotenv
import os


# =========================
# LOAD ENVIRONMENT
# =========================

load_dotenv

app = Flask(__name__)
app.secret_key = "acsi_voting_secret"

SUPABASE_URL =("https://jawfrnmrrniruafdetft.supabase.co")
SUPABASE_KEY =("eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imphd2Zybm1ycm5pcnVhZmRldGZ0Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3OTA1OTcxMzMsImV4cCI6MjEwNjE3MzEzM30.mg-3FX3Q6tqUu-l93t3QTjYpano9OtaFRsgmX0EjdnE")
 
print("SUPABASE_URL:", SUPABASE_URL)

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)


@app.route("/")
def home():
    return render_template("index.html")


@app.route('/vlogin', methods=['GET', 'POST'])
def vlogin():

    if request.method == 'POST':

        student_id = request.form.get('student_id', '').strip()
        password = request.form.get('password', '').strip()

        # FIND VOTER
        voter_result = supabase.table('voters') \
            .select('*') \
            .eq('student_id', student_id) \
            .execute()

        if not voter_result.data:
            flash("Voter not found, register first.", "error")
            return redirect(url_for('vlogin'))

        voter = voter_result.data[0]

        # CHECK PASSWORD
        if str(voter.get('password', '')).strip() != password:
            flash("Incorrect password.", "error")
            return redirect(url_for('vlogin'))

        # SAVE LOGIN SESSION
        session['student_id'] = voter['student_id']
        session['student_name'] = voter['student_name']
        session['course'] = voter.get('course', '')
        
        # IMPORTANT:
        # DO NOT CHECK Voted STATUS HERE.
        # Voted voters can still enter the dashboard.

        return redirect(url_for('vdashboard'))

    return render_template('vlogin.html')








@app.route('/vdashboard')
def vdashboard():

    student_id = session.get('student_id')

    if not student_id:
        return redirect(url_for('vlogin'))

    # GET VOTER INFORMATION
    voter_result = supabase.table('voters') \
        .select('*') \
        .eq('student_id', student_id) \
        .execute()

    if not voter_result.data:
        return redirect(url_for('vlogin'))

    voter = voter_result.data[0]

    return render_template(
        'vdashboard.html',
        student_name=voter['student_name'],
        student_id=voter['student_id'],
        course=voter['course'],
        status=voter['status']
    )







































        


@app.route('/register', methods=['GET', 'POST'])
def register():

    if request.method == 'POST':

        student_id = request.form.get('student_id')
        student_name = request.form.get('student_name')
        course = request.form.get('course')

        # Check if Student ID is exactly 9 digits
        if not student_id or not student_id.isdigit() or len(student_id) != 9:
            flash("Please enter exactly 9 digits.", "error")
            return redirect('/register')

        # Check if all fields are filled
        if not student_name or not course:
            flash("Please fill in all fields.", "error")
            return redirect('/register')

        # Check if Student ID is already registered
        existing_voter = supabase.table('voters') \
            .select('id') \
            .eq('student_id', student_id) \
            .execute()

        if existing_voter.data:
            flash("This Student ID is already registered. Please login.", "error")
            return redirect('/vlogin')

        # Automatically generate password using first name
        first_name = student_name.strip().split()[0]
        password = first_name

        # Register student
        new_voter = {
            "student_id": student_id,
            "student_name": student_name,
            "password": password,
            "status": "Not Yet Voted",
            "course": course
        }

        result = supabase.table('voters').insert(new_voter).execute()

        if result.data:
            flash("Registration successful! Your password is your first name.", "success")
            return redirect('/vlogin')

        flash("Registration failed. Please try again.", "error")
        return redirect('/register')

    return render_template('register.html')






@app.route('/votingpage')
def votingpage():

    # CHECK LOGIN
    student_id = session.get('student_id')

    if not student_id:
        return redirect(url_for('vlogin'))

    # GET VOTER
    voter_result = supabase.table('voters') \
        .select('*') \
        .eq('student_id', student_id) \
        .execute()

    if not voter_result.data:
        return redirect(url_for('vlogin'))

    voter = voter_result.data[0]

    student_name = voter.get('student_name', '')
    course = voter.get('course', '')

    # CHECK VOTER STATUS
    status = str(voter.get('status', '')).strip().lower()

    # IF ALREADY VOTED, BLOCK VOTING PAGE
    if status == 'voted':
        flash('You have already voted. You cannot vote again.', 'error')
        return redirect(url_for('vdashboard'))

    # IF STATUS IS NOT VALID
    if status != 'not yet voted':
        flash('Invalid voter status: ' + status, 'error')
        return redirect(url_for('vdashboard'))

    # GET POSITIONS
    positions_result = supabase.table('positions') \
        .select('*') \
        .order('id') \
        .execute()

    positions = positions_result.data or []

    # GET CANDIDATES
    candidates_result = supabase.table('candidates') \
        .select('*') \
        .order('id') \
        .execute()

    candidates = candidates_result.data or []

    # GET ACTIVE PARTYLISTS
    partylist_result = supabase.table('partylist') \
        .select('id') \
        .execute()

    partylist_ids = {
        str(p['id']).strip()
        for p in (partylist_result.data or [])
    }

    # KEEP ONLY CANDIDATES WHOSE PARTYLIST STILL EXISTS
    valid_candidates = []

    for candidate in candidates:

        candidate_partylist_id = str(
            candidate.get('partylist_id', '')
        ).strip()

        if candidate_partylist_id in partylist_ids:
            valid_candidates.append(candidate)

    candidates = valid_candidates

    # CONNECT CANDIDATES TO POSITION
    for position in positions:

        position['candidates'] = []

        for candidate in candidates:

            if str(candidate.get('position_id')).strip() == \
               str(position.get('id')).strip():

                position['candidates'].append(candidate)

    return render_template(
        'votingpage.html',
        student_id=student_id,
        student_name=student_name,
        course=course,
        positions=positions
    )








@app.route('/submit_vote', methods=['POST'])
def submit_vote():

    student_id = request.form.get('student_id')

    if not student_id:
        return redirect(url_for('vlogin'))

    # =========================
    # GET VOTER
    # =========================
    voter_result = supabase.table('voters') \
        .select('*') \
        .eq('student_id', student_id) \
        .execute()

    if not voter_result.data:
        return redirect(url_for('vlogin'))

    voter = voter_result.data[0]

    student_name = voter.get('student_name', '')
    course = voter.get('course', '')

    # =========================
    # CHECK IF ALREADY VOTED
    # =========================
    existing_vote = supabase.table('votes') \
        .select('*') \
        .eq('student_id', student_id) \
        .execute()

    # If already voted, don't insert again
    if existing_vote.data:
        return "You have already voted."

    # =========================
    # GET POSITIONS
    # =========================
    positions_result = supabase.table('positions') \
        .select('*') \
        .order('id') \
        .execute()

    positions = positions_result.data or []

    selected_votes = {}

    # =========================
    # GET SELECTED CANDIDATES
    # =========================
    for position in positions:

        position_id = position.get('id')
        position_name = position.get('position_name', '')

        # Representative belongs only
        # to the voter's course
        if 'representative' in position_name.lower():

            if course.upper().strip() not in position_name.upper():
                continue

        selected_candidate = request.form.get(
            f'position_{position_id}'
        )

        if not selected_candidate:
            return f"Please select a candidate for {position_name}."

        selected_votes[position_name] = selected_candidate

    # =========================
    # PREPARE VOTE DATA
    # =========================
    vote_data = {
        'student_id': student_id,
        'student_name': student_name
    }

    for position_name, candidate_name in selected_votes.items():

        column_name = position_name.lower().strip()

        column_name = column_name.replace(' ', '_')

        vote_data[column_name] = candidate_name

    # =========================
    # SAVE TO DATABASE
    # =========================
    supabase.table('votes').insert(vote_data).execute()
   
    supabase.table('voters').update({'status':'Voted'}) \
    .eq('student_id', student_id) \
    .execute()

    # =========================
    # CONFIRMATION PAGE
    # =========================
    return render_template(
        'confirmationpage.html',
        student_name=student_name,
        student_id=student_id,
        course=course,
        selected_votes=selected_votes
    )









@app.route('/adminlogin', methods=['GET', 'POST'])
def adminlogin():

    if request.method == 'POST':

        username = request.form.get('username')
        password = request.form.get('password')

        # Check empty fields
        if not username or not password:
            return render_template(
                'adminlogin.html',
                error='Please enter username and password'
            )

        # Your admin account
        if username != 'admin':
            return render_template(
                'adminlogin.html',
                error='Incorrect username'
            )

        if password != 'admin123':
            return render_template(
                'adminlogin.html',
                error='Incorrect password'
            )

        # Correct login
        session['admin_logged_in'] = True

        return redirect(url_for('dashboard'))

    return render_template('adminlogin.html')

@app.route('/dashboard')
def dashboard():

    if not session.get('admin_logged_in'):
        return redirect(url_for('adminlogin'))

    return render_template('admindashboard.html')




@app.route("/admin_logout")
def admin_logout():

    session.pop("admin_logged_in", None)

    return redirect(url_for("adminlogin"))



# =========================
# VIEW VOTERS
# =========================
@app.route('/viewvoters')
def view_voters():

    if not session.get('admin_logged_in'):
        return redirect(url_for('adminlogin'))

    # Get all voters from Supabase
    result = supabase.table('voters').select('*').execute()
    voters = result.data

    return render_template(
        'viewvoters.html',
        voters=voters
    )

@app.route('/managecandidates')
def managecandidates():

    position_result = supabase.table('positions') \
        .select('*') \
        .order('id') \
        .execute()

    partylist_result = supabase.table('partylist') \
        .select('*') \
        .order('id') \
        .execute()

    candidate_result = supabase.table('candidates') \
        .select('*') \
        .order('id') \
        .execute()

    positions = position_result.data or []
    partylists = partylist_result.data or []
    candidates = candidate_result.data or []

    # Add position name to every candidate
    for candidate in candidates:

        candidate['position_name'] = ''

        for position in positions:

            if candidate.get('position_id') == position.get('id'):

                candidate['position_name'] = position.get('position_name')
                break

    return render_template(
        'managecandidates.html',
        positions=positions,
        partylists=partylists,
        candidates=candidates
    )

@app.route('/canparty')
def canparty():

    # Get all partylists
    partylists = supabase.table('partylist').select('*').execute().data

    # Get all candidates
    candidates = supabase.table('candidates').select('*').execute().data

    # Get all positions
    positions = supabase.table('positions').select('*').execute().data

    # Create position lookup
    position_lookup = {}

    for position in positions:
        position_lookup[position['id']] = position['position_name']

    # Add position name to every candidate
    for candidate in candidates:
        candidate['position_name'] = position_lookup.get(
            candidate['position_id'],
            'Unknown Position'
        )

    return render_template(
        'canparty.html',
        partylists=partylists,
        candidates=candidates
    )


@app.route('/add_candidate', methods=['POST'])
def add_candidate():

    try:
        # Get selected partylist
        partylist_id = request.form.get('partylist_id')

        if not partylist_id:
            flash('Please select a partylist.', 'error')
            return redirect(url_for('managecandidates'))

        # Position fields and their corresponding POSITION_ID
        positions = [
            ('president', 1),
            ('vice_president', 2),
            ('secretary', 3),
            ('treasurer', 4),
            ('auditor', 5),
            ('public_info_officer', 6),
            ('bscs_representative', 7),
            ('bsis_representative', 8),
            ('act_representative', 9),
            ('shs_representative', 10)
        ]

        candidates_to_add = []

        # Check every position
        for field_name, position_id in positions:

            candidate_name = request.form.get(field_name)

            # Only save fields that have a name
            if candidate_name and candidate_name.strip():

                candidates_to_add.append({
                    'full_name': candidate_name.strip(),
                    'position_id': position_id,
                    'partylist_id': int(partylist_id)
                })

        # Make sure at least one candidate was entered
        if not candidates_to_add:
            flash('Please enter at least one candidate name.', 'error')
            return redirect(url_for('managecandidates'))

        # Insert all candidates at once
        supabase.table('candidates') \
            .insert(candidates_to_add) \
            .execute()

        flash('Candidates added successfully!', 'success')

    except Exception as e:

        flash(f'Error adding candidates: {str(e)}', 'error')

    return redirect(url_for('managecandidates'))


@app.route('/results')
def results():

    # GET ALL CANDIDATES
    candidates_result = supabase.table('candidates').select('*').execute()
    candidates = candidates_result.data or []

    # GET ALL VOTES
    votes_result = supabase.table('votes').select('*').execute()
    votes = votes_result.data or []

    # GET ALL POSITIONS
    positions_result = supabase.table('positions').select('*').execute()
    positions = positions_result.data or []

    # POSITION ORDER
    position_order = [
        "President",
        "Vice President",
        "Secretary",
        "Treasurer",
        "Auditor",
        "Public Information Officer",
        "BSCS Representative",
        "BSIS Representative",
        "ACT Representative",
        "SHS Representative"
    ]

    # SORT POSITIONS
    positions = sorted(
        positions,
        key=lambda x: (
            position_order.index(x["position_name"])
            if x["position_name"] in position_order
            else 999
        )
    )

    # VOTE COLUMN MAPPING
    vote_columns = {
        "President": "president",
        "Vice President": "vice_president",
        "Secretary": "secretary",
        "Treasurer": "treasurer",
        "Auditor": "auditor",
        "Public Information Officer": "public_information_officer",
        "BSCS Representative": "bscs_representative",
        "BSIS Representative": "bsis_representative",
        "ACT Representative": "act_representative",
        "SHS Representative": "shs_representative"
    }

    results_data = []

    # LOOP THROUGH POSITIONS
    for position in positions:

        position_id = position["id"]
        position_name = position["position_name"]

        vote_column = vote_columns.get(position_name)

        # GET CANDIDATES FOR THIS POSITION
        position_candidates = []

        for candidate in candidates:

            if candidate["position_id"] == position_id:
                position_candidates.append(candidate)

        # COUNT VOTES
        candidate_results = []

        for candidate in position_candidates:

            candidate_name = str(candidate["full_name"]).strip()

            vote_count = 0

            for vote in votes:

                selected_candidate = vote.get(vote_column)

                if selected_candidate is not None:

                    selected_candidate = str(
                        selected_candidate
                    ).strip()

                    if selected_candidate.lower() == candidate_name.lower():

                        vote_count += 1

            candidate_results.append({
                "name": candidate_name,
                "votes": vote_count
            })

        # ADD POSITION RESULTS
        results_data.append({
            "name": position_name,
            "candidates": candidate_results
        })

         # DISPLAY RESULTS
    return render_template(
        "results.html",
        results=results_data
    )






@app.route('/delete_partylist/<int:partylist_id>', methods=['POST'])
def delete_partylist(partylist_id):

    if not session.get('admin_logged_in'):
        return redirect(url_for('adminlogin'))

    try:
        # Delete candidates under this partylist first
        supabase.table('candidates') \
            .delete() \
            .eq('partylist_id', partylist_id) \
            .execute()

        # Then delete the partylist
        result = supabase.table('partylist') \
            .delete() \
            .eq('id', partylist_id) \
            .execute()

        if result.data:
            flash('Partylist and its candidates deleted successfully', 'success')
        else:
            flash('Partylist was not deleted', 'error')

    except Exception as e:
        print("DELETE ERROR:", e)
        flash(f'Delete error: {e}', 'error')

    return redirect(url_for('canparty'))


@app.route('/add_partylist', methods=['POST'])
def add_partylist():

    partylist_name = request.form.get('partylist_name', '').strip()
    Platform = request.form.get('Platform', '').strip()

    print("PARTYLIST NAME:", partylist_name)
    print("PLATFORM:", Platform)

    if partylist_name == '':
        return "Partylist name is required"

    data = {
        'partylist_name': partylist_name,
        'Platform': Platform
    }


    flash('PartyList added successfully!', 'success')

    result = supabase.table('partylist').insert(data).execute()

    return redirect(url_for('managecandidates'))














 
if __name__ == "__main__":
    app.run(debug=True)