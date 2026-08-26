const API_BASE = "http://127.0.0.1:8000/api";
let currentQuizCourseId = null;
let currentQuizQuestions = [];

function toggleForm() {
  const isLogin = document.getElementById("login-form").classList.toggle("hidden");
  document.getElementById("register-form").classList.toggle("hidden");
  document.getElementById("form-title").innerText = isLogin ? "Officer Registration" : "Officer Login";
  document.getElementById("toggle-form-btn").innerText = isLogin ? "Already registered? Login here" : "New Officer? Register here";
}

function fillDemo() {
  document.getElementById("login-email").value = "emp@mospi.gov.in";
  document.getElementById("login-password").value = "password123";
}

// Authentication Handlers
const loginForm = document.getElementById("login-form");
if (loginForm) {
  loginForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const email = document.getElementById("login-email").value;
    const password = document.getElementById("login-password").value;
    try {
      const res = await fetch(`${API_BASE}/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      localStorage.setItem("userEmail", data.user.email);
      window.location.href = "dashboard.html";
    } catch (err) {
      alert("Login Failed: " + err.message);
    }
  });
}

const regForm = document.getElementById("register-form");
if (regForm) {
  regForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const payload = {
      name: document.getElementById("reg-name").value,
      email: document.getElementById("reg-email").value,
      password: document.getElementById("reg-password").value,
      department: document.getElementById("reg-dept").value,
      designation: document.getElementById("reg-desig").value,
    };
    try {
      const res = await fetch(`${API_BASE}/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail);
      localStorage.setItem("userEmail", payload.email);
      alert("Registration Successful! Redirecting to Dashboard...");
      window.location.href = "dashboard.html";
    } catch (err) {
      alert("Registration Failed: " + err.message);
    }
  });
}

// Dashboard Loader
async function loadDashboard() {
  const email = localStorage.getItem("userEmail") || "emp@mospi.gov.in";

  try {
    const res = await fetch(`${API_BASE}/dashboard/${email}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail);

    document.getElementById("nav-user-name").innerText = data.profile.name;
    document.getElementById("prof-name").innerText = data.profile.name;
    document.getElementById("prof-desig").innerText = data.profile.designation;
    document.getElementById("prof-dept").innerText = data.profile.department;

    document.getElementById("stat-score").innerText = `${data.profile.competency_score}%`;
    document.getElementById("stat-bar").style.width = `${data.profile.competency_score}%`;
    document.getElementById("stat-modules-done").innerText = `${data.stats.completed_count}/${data.stats.total_courses} Modules Cleared`;

    // Render Pending Courses
    const todoContainer = document.getElementById("todo-list");
    todoContainer.innerHTML = data.todo_courses.length ? "" : `<p class="text-xs text-slate-400 col-span-full">All assigned competency modules completed!</p>`;
    
    data.todo_courses.forEach((c) => {
      const quizBtn = c.video_completed 
        ? `<button onclick="openQuiz('${c.course_id}', '${c.title}')" class="flex-1 bg-emerald-700 hover:bg-emerald-800 text-white text-xs font-bold py-2 rounded-xl transition shadow">Take Quiz (Unlocked) →</button>`
        : `<button disabled class="flex-1 bg-slate-200 text-slate-400 cursor-not-allowed text-xs font-bold py-2 rounded-xl">🔒 Quiz Locked (Watch Video First)</button>`;

      todoContainer.innerHTML += `
        <div class="bg-white rounded-2xl border border-slate-200 p-5 shadow-sm space-y-4 flex flex-col justify-between">
          <div class="space-y-2">
            <div class="flex justify-between items-center">
              <span class="text-[10px] font-black uppercase bg-blue-100 text-blue-900 px-2.5 py-0.5 rounded-full">${c.domain}</span>
              <span class="text-[11px] font-mono text-slate-400">${c.course_id}</span>
            </div>
            <h4 class="font-bold text-sm text-slate-800">${c.title}</h4>
            <p class="text-xs text-slate-500">${c.description}</p>
          </div>

          <div class="aspect-video w-full rounded-xl overflow-hidden bg-black shadow-inner">
            <iframe class="w-full h-full" src="${c.video_url}" allowfullscreen></iframe>
          </div>

          <div class="space-y-2 pt-2 border-t">
            <div class="flex space-x-2">
              <button onclick="markVideoDone('${c.course_id}')" class="px-3 py-2 bg-blue-50 text-blue-900 hover:bg-blue-100 rounded-xl text-xs font-bold transition">
                ${c.video_completed ? "✓ Video Watched" : "Mark Video Watched"}
              </button>
              ${quizBtn}
            </div>
            
            <label class="block text-center w-full border border-dashed border-slate-300 hover:border-slate-400 text-slate-600 text-[11px] py-1.5 rounded-xl cursor-pointer transition">
              Upload Certificate to Auto-Verify
              <input type="file" accept=".pdf" class="hidden" onchange="uploadCert(event, '${c.course_id}')" />
            </label>
          </div>
        </div>
      `;
    });

    // Render Completed Courses
    const compContainer = document.getElementById("completed-list");
    compContainer.innerHTML = data.completed_courses.length ? "" : `<p class="text-xs text-slate-400 col-span-full">No completed modules yet.</p>`;
    data.completed_courses.forEach((c) => {
      compContainer.innerHTML += `
        <div class="bg-emerald-50/70 rounded-2xl border border-emerald-200 p-4 space-y-1">
          <div class="flex justify-between items-center">
            <span class="text-xs font-bold text-slate-800">${c.title}</span>
            <span class="text-[10px] font-black bg-emerald-100 text-emerald-800 px-2 py-0.5 rounded">Verified</span>
          </div>
          <p class="text-[11px] text-slate-500">Score: ${c.quiz_score} Pts • Domain: ${c.domain}</p>
        </div>
      `;
    });
  } catch (err) {
    alert("Error loading dashboard: " + err.message);
  }
}

async function markVideoDone(courseId) {
  const email = localStorage.getItem("userEmail") || "emp@mospi.gov.in";
  try {
    const res = await fetch(`${API_BASE}/complete-video`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, course_id: courseId }),
    });
    if (!res.ok) throw new Error("Failed to update status");
    loadDashboard();
  } catch (err) {
    alert(err.message);
  }
}

async function uploadCert(e, courseId) {
  const file = e.target.files[0];
  if (!file) return;

  const email = localStorage.getItem("userEmail") || "emp@mospi.gov.in";
  const formData = new FormData();
  formData.append("email", email);
  formData.append("course_id", courseId);
  formData.append("file", file);

  try {
    const res = await fetch(`${API_BASE}/verify-certificate`, { method: "POST", body: formData });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail);
    alert(data.message);
    loadDashboard();
  } catch (err) {
    alert("Verification Failed: " + err.message);
  }
}

// Assessment / Quiz Operations
async function openQuiz(courseId, title) {
  currentQuizCourseId = courseId;
  document.getElementById("quiz-title").innerText = `Assessment: ${title}`;
  document.getElementById("quiz-submit-btn").classList.remove("hidden");
  document.getElementById("quiz-close-btn").classList.add("hidden");
  document.getElementById("quiz-feedback-box").classList.add("hidden");

  const container = document.getElementById("quiz-questions-container");
  container.innerHTML = "<p class='text-xs text-slate-400'>Loading questions...</p>";
  document.getElementById("quiz-modal").classList.remove("hidden");
  document.getElementById("quiz-modal").classList.add("flex");

  try {
    const res = await fetch(`${API_BASE}/quiz/${courseId}`);
    const data = await res.json();
    currentQuizQuestions = data.questions;

    if (!currentQuizQuestions.length) {
      container.innerHTML = `<p class="text-xs text-slate-500">No questions available for this module.</p>`;
      return;
    }

    container.innerHTML = currentQuizQuestions
      .map(
        (q, qIdx) => `
      <div class="border border-slate-200 rounded-xl p-3.5 bg-slate-50 space-y-2">
        <p class="font-bold text-xs text-slate-800">${qIdx + 1}. ${q.question}</p>
        <div class="space-y-1.5">
          ${q.options
            .map(
              (opt, oIdx) => `
            <label class="flex items-center space-x-2.5 text-xs text-slate-700 cursor-pointer p-1.5 rounded-lg hover:bg-white transition border border-transparent hover:border-slate-200">
              <input type="radio" name="q_${qIdx}" value="${oIdx}" />
              <span>${opt}</span>
            </label>
          `
            )
            .join("")}
        </div>
      </div>
    `
      )
      .join("");
  } catch (err) {
    container.innerHTML = "Error loading quiz.";
  }
}

function closeQuizModal() {
  document.getElementById("quiz-modal").classList.add("hidden");
  document.getElementById("quiz-modal").classList.remove("flex");
}

async function submitCurrentQuiz() {
  const email = localStorage.getItem("userEmail") || "emp@mospi.gov.in";
  const answers = [];

  for (let i = 0; i < currentQuizQuestions.length; i++) {
    const sel = document.querySelector(`input[name="q_${i}"]:checked`);
    if (!sel) {
      alert(`Please answer question #${i + 1}`);
      return;
    }
    answers.push(parseInt(sel.value));
  }

  try {
    const res = await fetch(`${API_BASE}/submit-quiz`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, course_id: currentQuizCourseId, answers }),
    });
    const result = await res.json();

    const fbBox = document.getElementById("quiz-feedback-box");
    fbBox.classList.remove("hidden");
    fbBox.className = result.passed ? "p-4 rounded-xl text-xs space-y-3 bg-emerald-50 border border-emerald-200" : "p-4 rounded-xl text-xs space-y-3 bg-rose-50 border border-rose-200";

    fbBox.innerHTML = `
      <div class="font-bold text-sm ${result.passed ? 'text-emerald-800' : 'text-rose-800'}">
        ${result.passed ? '✓ Assessment Passed!' : '✕ Score below 50%'} (Score: ${result.score}/${result.total})
      </div>
      <div class="space-y-2 mt-2">
        ${result.review.map(r => `
          <div class="p-2 bg-white rounded border ${r.is_correct ? 'border-emerald-200' : 'border-rose-200'}">
            <p class="font-semibold text-slate-800">${r.question}</p>
            <p class="${r.is_correct ? 'text-emerald-700' : 'text-rose-700'} font-bold mt-0.5">
              ${r.is_correct ? 'Correct' : 'Incorrect'} (Correct: ${r.options[r.correct_answer]})
            </p>
            <p class="text-[11px] text-slate-500 mt-0.5">${r.explanation}</p>
          </div>
        `).join("")}
      </div>
    `;

    document.getElementById("quiz-submit-btn").classList.add("hidden");
    document.getElementById("quiz-close-btn").classList.remove("hidden");

    if (result.passed) {
      loadDashboard();
    }
  } catch (err) {
    alert("Submission error: " + err.message);
  }
}

function logout() {
  localStorage.clear();
  window.location.href = "index.html";
}