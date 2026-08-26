const API_BASE = "http://127.0.0.1:8000/api";

async function loadAdminData() {
  try {
    const res = await fetch(`${API_BASE}/admin/analytics`);
    const data = await res.json();

    document.getElementById("admin-total-officers").innerText = data.total_officers;
    document.getElementById("admin-total-courses").innerText = data.total_courses;

    // Render Designation Summary
    const cadreBody = document.getElementById("cadre-table-body");
    cadreBody.innerHTML = "";
    data.cadre_summary.forEach(c => {
      cadreBody.innerHTML += `
        <tr class="border-b hover:bg-slate-50">
          <td class="p-3 font-semibold text-slate-800">${c.designation}</td>
          <td class="p-3">${c.count} Officers</td>
          <td class="p-3 font-bold text-blue-900">${c.avg_score}%</td>
        </tr>
      `;
    });

    // Render Live Officer Roster
    const rosterBody = document.getElementById("roster-table-body");
    rosterBody.innerHTML = "";
    data.roster.forEach(r => {
      rosterBody.innerHTML += `
        <tr class="border-b hover:bg-slate-50">
          <td class="p-3 font-bold text-slate-800">${r.name}<br><span class="text-[10px] text-slate-400 font-normal">${r.email}</span></td>
          <td class="p-3">${r.designation}<br><span class="text-[10px] text-slate-400">${r.department}</span></td>
          <td class="p-3"><span class="px-2 py-0.5 bg-blue-100 text-blue-900 rounded font-bold">${r.competency_score}%</span></td>
          <td class="p-3 font-semibold text-emerald-700">${r.completed_count} Modules</td>
          <td class="p-3 text-[11px] text-rose-600 font-medium">${r.pending_courses.join(", ") || "None (All Complete)"}</td>
        </tr>
      `;
    });
  } catch (err) {
    console.error("Error loading analytics: ", err);
  }
}

async function handlePdfUpload(e) {
  e.preventDefault();
  const courseId = document.getElementById("upload-course-id").value;
  const file = document.getElementById("upload-pdf-file").files[0];
  const msgEl = document.getElementById("admin-upload-msg");

  const formData = new FormData();
  formData.append("course_id", courseId);
  formData.append("file", file);

  try {
    const res = await fetch(`${API_BASE}/admin/generate-quiz-pdf`, {
      method: "POST",
      body: formData,
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail);

    msgEl.innerText = `✓ ${data.message}`;
    msgEl.classList.remove("hidden");
    loadAdminData();
  } catch (err) {
    alert("Generation Error: " + err.message);
  }
}