const { createApp } = Vue;

/**
 * Create the main IIT Madras Placement Portal Vue application.
 *
 * This SPA controls routing via a simple `currentPage` string and communicates
 * with the Flask backend using fetch() with JWT Authorization headers.
 */
createApp({
  data() {
    return {
      token: localStorage.getItem('ppa_token') || null,
      currentUser: null,
      currentPage: 'login',
      isLoading: false,
      toast: { show: false, message: '', type: 'success' },
      // Auth forms
      loginForm: { email: '', password: '' },
      studentRegisterForm: {
        email: '',
        password: '',
        full_name: '',
        roll_number: '',
        branch: '',
        year_of_passout: '',
        cgpa: '',
        phone: ''
      },
      // Separate field to hold the selected resume file during student registration
      studentRegisterResumeFile: null,
      companyRegisterForm: {
        email: '',
        password: '',
        company_name: '',
        hr_name: '',
        hr_email: '',
        website: '',
        description: ''
      },
      // Admin state
      adminDashboard: null,
      adminCompanies: [],
      adminCompaniesSearch: '',
      adminStudents: [],
      adminStudentsSearch: '',
      adminDrives: [],
      adminApplications: [],
      adminAnalytics: null,
      // Company state
      companyProfile: null,
      companyDrives: [],
      companyDriveForm: {
        job_title: '',
        job_description: '',
        eligible_branches: [],
        min_cgpa: '',
        eligible_passout_year: '',
        package_lpa: '',
        application_deadline: ''
      },
      companyDriveApplications: [],
      companySelectedDriveId: null,
      companyBranches: ['CSE', 'ECE', 'EE', 'ME', 'CE'],
      // Student state
      studentProfile: null,
      studentDashboardDrives: [],
      studentSelectedDrive: null,
      studentDashboardFilters: {
        search: '',
        branch: '',
        min_cgpa: '',
        year: ''
      },
      studentApplications: [],
      exportJobPollingId: null,
      studentFilterDebounceId: null,
      // Chart instances
      charts: {
        drivesPerMonth: null,
        statusBreakdown: null,
        topCompanies: null,
        monthlySelections: null
      }
    };
  },

  computed: {
    /**
     * Check if the current user is an admin.
     *
     * @returns {boolean} True if user role is 'admin'.
     */
    isAdmin() {
      return this.currentUser && this.currentUser.role === 'admin';
    },

    /**
     * Check if the current user is a company.
     *
     * @returns {boolean} True if user role is 'company'.
     */
    isCompany() {
      return this.currentUser && this.currentUser.role === 'company';
    },

    /**
     * Check if the current user is a student.
     *
     * @returns {boolean} True if user role is 'student'.
     */
    isStudent() {
      return this.currentUser && this.currentUser.role === 'student';
    }
  },

  methods: {
    /**
     * Reset all non-auth application state to its initial values.
     *
     * @returns {void}
     */
    resetState() {
      this.loginForm = { email: '', password: '' };
      this.studentRegisterForm = {
        email: '',
        password: '',
        full_name: '',
        roll_number: '',
        branch: '',
        year_of_passout: '',
        cgpa: '',
        phone: ''
      };
      this.studentRegisterResumeFile = null;
      this.companyRegisterForm = {
        email: '',
        password: '',
        company_name: '',
        hr_name: '',
        hr_email: '',
        website: '',
        description: ''
      };
      this.adminDashboard = null;
      this.adminCompanies = [];
      this.adminCompaniesSearch = '';
      this.adminStudents = [];
      this.adminStudentsSearch = '';
      this.adminDrives = [];
      this.adminApplications = [];
      this.adminAnalytics = null;
      this.companyProfile = null;
      this.companyDrives = [];
      this.companyDriveForm = {
        job_title: '',
        job_description: '',
        eligible_branches: [],
        min_cgpa: '',
        eligible_passout_year: '',
        package_lpa: '',
        application_deadline: ''
      };
      this.companyDriveApplications = [];
      this.companySelectedDriveId = null;
      this.studentProfile = null;
      this.studentDashboardDrives = [];
      this.studentSelectedDrive = null;
      this.studentDashboardFilters = {
        search: '',
        branch: '',
        min_cgpa: '',
        year: ''
      };
      this.studentApplications = [];
      if (this.exportJobPollingId) {
        clearInterval(this.exportJobPollingId);
        this.exportJobPollingId = null;
      }
      if (this.charts.drivesPerMonth) this.charts.drivesPerMonth.destroy();
      if (this.charts.statusBreakdown) this.charts.statusBreakdown.destroy();
      if (this.charts.topCompanies) this.charts.topCompanies.destroy();
      if (this.charts.monthlySelections) this.charts.monthlySelections.destroy();
      this.charts = {
        drivesPerMonth: null,
        statusBreakdown: null,
        topCompanies: null,
        monthlySelections: null
      };
    },
    /**
     * Perform an API call to the Flask backend using fetch().
     *
     * @param {string} method - HTTP method (GET, POST, etc.).
     * @param {string} url - Endpoint path (e.g., '/api/auth/login').
     * @param {Object|FormData|null} body - Request payload.
     * @param {boolean} isFormData - Whether the body is FormData.
     * @returns {Promise<Object>} Parsed JSON response.
     */
    async apiCall(method, url, body = null, isFormData = false) {
      this.isLoading = true;
      try {
        const headers = {};
        if (!isFormData) {
          headers['Content-Type'] = 'application/json';
        }
        if (this.token) {
          headers['Authorization'] = `Bearer ${this.token}`;
        }

        const options = { method, headers };
        if (body) {
          options.body = isFormData ? body : JSON.stringify(body);
        }

        const res = await fetch(url, options);
        const data = await res.json().catch(() => ({ success: false, error: 'Invalid JSON response from server.' }));
        if (!res.ok || data.success === false) {
          const errorMessage = data && data.error ? data.error : `Request failed with status ${res.status}`;
          throw new Error(errorMessage);
        }
        return data;
      } finally {
        this.isLoading = false;
      }
    },

    /**
     * Fetch a protected file using JWT and return Response.
     *
     * @param {string} url
     * @returns {Promise<Response>}
     */
    async fetchProtected(url) {
      const headers = {};
      if (this.token) {
        headers['Authorization'] = `Bearer ${this.token}`;
      }
      const res = await fetch(url, { method: 'GET', headers });
      if (!res.ok) {
        // Try to parse JSON error, otherwise use status.
        const data = await res.json().catch(() => null);
        const msg = data && data.error ? data.error : `Request failed with status ${res.status}`;
        throw new Error(msg);
      }
      return res;
    },

    /**
     * Download a protected file (CSV/DOC/PDF) using JWT.
     *
     * @param {string} url
     * @param {string} fallbackName
     * @returns {Promise<void>}
     */
    async downloadProtectedFile(url, fallbackName) {
      const res = await this.fetchProtected(url);
      const blob = await res.blob();
      const blobUrl = URL.createObjectURL(blob);

      // Try to infer a filename from Content-Disposition.
      const cd = res.headers.get('Content-Disposition') || '';
      const match = cd.match(/filename="?([^"]+)"?/i);
      const filename = (match && match[1]) ? match[1] : fallbackName;

      const a = document.createElement('a');
      a.href = blobUrl;
      a.download = filename || 'download';
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(blobUrl), 1000);
    },

    /**
     * Open a protected file in a new tab (HTML/PDF) using JWT.
     *
     * @param {string} url
     * @param {string} mimeHint
     * @returns {Promise<void>}
     */
    async openProtectedFile(url, mimeHint = '') {
      const res = await this.fetchProtected(url);
      const blob = await res.blob();
      const type = blob.type || mimeHint || 'application/octet-stream';
      const blobUrl = URL.createObjectURL(new Blob([blob], { type }));
      window.open(blobUrl, '_blank', 'noopener');
      // revoke later (allow browser time to load)
      setTimeout(() => URL.revokeObjectURL(blobUrl), 60_000);
    },

    /**
     * Navigate to a given page identifier.
     *
     * @param {string} page - Target page name.
     * @returns {void}
     */
    navigateTo(page) {
      this.currentPage = page;
    },

    /**
     * Show a Bootstrap-like toast using reactive state.
     *
     * @param {string} message - Message to display.
     * @param {string} type - 'success' or 'danger' for styling.
     * @returns {void}
     */
    showToast(message, type = 'success') {
      this.toast = { show: true, message, type };
      setTimeout(() => {
        this.toast.show = false;
      }, 4000);
    },

    /**
     * Clear authentication state and navigate back to login page.
     *
     * @returns {void}
     */
    logout() {
      this.token = null;
      this.currentUser = null;
      localStorage.removeItem('ppa_token');
      this.resetState();
      this.navigateTo('login');
      this.showToast('Logged out successfully.', 'success');
    },

    /**
     * Handle login form submission.
     *
     * @returns {Promise<void>}
     */
    async submitLogin() {
      try {
        const payload = {
          email: this.loginForm.email,
          password: this.loginForm.password
        };
        const res = await this.apiCall('POST', '/api/auth/login', payload);
        const data = res.data;
        this.token = data.token;
        localStorage.setItem('ppa_token', this.token);
        this.currentUser = { id: data.user_id, role: data.role, name: data.name };
        this.showToast('Login successful.', 'success');
        this.navigateAfterLogin();
      } catch (err) {
        this.showToast(err.message || 'Login failed.', 'danger');
      }
    },

    /**
     * Decide landing page after login based on role.
     *
     * @returns {void}
     */
    navigateAfterLogin() {
      if (this.isAdmin) {
        this.navigateTo('adminDashboard');
        this.loadAdminDashboard();
      } else if (this.isCompany) {
        this.navigateTo('companyDashboard');
        this.loadCompanyDashboard();
      } else if (this.isStudent) {
        this.navigateTo('studentDashboard');
        this.loadStudentDashboard();
      } else {
        this.navigateTo('login');
      }
    },

    /**
     * Handle student registration form submission.
     *
     * @returns {Promise<void>}
     */
    async submitStudentRegister() {
      try {
        // Resume is compulsory at registration time.
        if (!this.studentRegisterResumeFile) {
          this.showToast('Please upload your resume before registering.', 'danger');
          return;
        }

        const payload = { ...this.studentRegisterForm };
        const res = await this.apiCall('POST', '/api/auth/register/student', payload);

        // Use the returned token to immediately upload the resume once.
        const token = res && res.data && res.data.token ? res.data.token : null;
        if (token) {
          const formData = new FormData();
          formData.append('resume', this.studentRegisterResumeFile);

          const uploadRes = await fetch('/api/student/profile/resume', {
            method: 'POST',
            headers: {
              Authorization: `Bearer ${token}`
            },
            body: formData
          });

          const uploadData = await uploadRes.json().catch(() => null);
          if (!uploadRes.ok || (uploadData && uploadData.success === false)) {
            const msg =
              (uploadData && (uploadData.error || uploadData.message)) ||
              `Resume upload failed with status ${uploadRes.status}`;
            throw new Error(msg);
          }
        }

        // After successful registration and resume upload, redirect to login instead of auto-login.
        this.showToast('Student registered successfully and resume uploaded. Please log in.', 'success');
        this.studentRegisterForm = {
          email: '',
          password: '',
          full_name: '',
          roll_number: '',
          branch: '',
          year_of_passout: '',
          cgpa: '',
          phone: ''
        };
        this.studentRegisterResumeFile = null;
        this.navigateTo('login');
      } catch (err) {
        this.showToast(err.message || 'Registration failed.', 'danger');
      }
    },

    /**
     * Handle resume file selection on the student registration form.
     *
     * @param {Event} event - File input change event.
     * @returns {void}
     */
    onStudentRegisterResumeChange(event) {
      const file = event.target.files && event.target.files[0];
      this.studentRegisterResumeFile = file || null;
    },

    /**
     * Handle company registration form submission.
     *
     * @returns {Promise<void>}
     */
    async submitCompanyRegister() {
      try {
        const payload = { ...this.companyRegisterForm };
        await this.apiCall('POST', '/api/auth/register/company', payload);
        // After successful registration, redirect to login instead of auto-login.
        this.showToast('Company registered successfully. Please wait for admin approval and log in.', 'success');
        this.companyRegisterForm = {
          email: '',
          password: '',
          company_name: '',
          hr_name: '',
          hr_email: '',
          website: '',
          description: ''
        };
        this.navigateTo('login');
      } catch (err) {
        this.showToast(err.message || 'Registration failed.', 'danger');
      }
    },

    /**
     * Load current user information from /api/auth/me.
     *
     * @returns {Promise<void>}
     */
    async loadCurrentUser() {
      if (!this.token) return;
      try {
        const res = await this.apiCall('GET', '/api/auth/me');
        const data = res.data;
        const user = data.user;
        this.currentUser = { id: user.id, role: user.role, name: data.name };
      } catch (err) {
        this.logout();
      }
    },

    /**
     * Load admin dashboard metrics and recent items.
     *
     * @returns {Promise<void>}
     */
    async loadAdminDashboard() {
      try {
        const res = await this.apiCall('GET', '/api/admin/dashboard');
        this.adminDashboard = res.data;
      } catch (err) {
        this.showToast(err.message || 'Unable to load admin dashboard.', 'danger');
      }
    },

    /**
     * Fetch companies for admin with optional search.
     *
     * @returns {Promise<void>}
     */
    async loadAdminCompanies() {
      try {
        const q = this.adminCompaniesSearch ? `?search=${encodeURIComponent(this.adminCompaniesSearch)}` : '';
        const res = await this.apiCall('GET', `/api/admin/companies${q}`);
        this.adminCompanies = res.data.companies;
      } catch (err) {
        this.showToast(err.message || 'Unable to load companies.', 'danger');
      }
    },

    /**
     * Fetch students for admin with optional search.
     *
     * @returns {Promise<void>}
     */
    async loadAdminStudents() {
      try {
        const q = this.adminStudentsSearch ? `?search=${encodeURIComponent(this.adminStudentsSearch)}` : '';
        const res = await this.apiCall('GET', `/api/admin/students${q}`);
        this.adminStudents = res.data.students;
      } catch (err) {
        this.showToast(err.message || 'Unable to load students.', 'danger');
      }
    },

    /**
     * Fetch all drives for admin.
     *
     * @returns {Promise<void>}
     */
    async loadAdminDrives() {
      try {
        const res = await this.apiCall('GET', '/api/admin/drives');
        this.adminDrives = res.data.drives;
      } catch (err) {
        this.showToast(err.message || 'Unable to load drives.', 'danger');
      }
    },

    /**
     * Fetch all applications for admin.
     *
     * @returns {Promise<void>}
     */
    async loadAdminApplications() {
      try {
        const res = await this.apiCall('GET', '/api/admin/applications');
        this.adminApplications = res.data.applications;
      } catch (err) {
        this.showToast(err.message || 'Unable to load applications.', 'danger');
      }
    },

    /**
     * Fetch analytics for admin and render Chart.js charts.
     *
     * @returns {Promise<void>}
     */
    async loadAdminAnalytics() {
      try {
        const res = await this.apiCall('GET', '/api/admin/analytics');
        this.adminAnalytics = res.data;
        this.$nextTick(() => {
          this.renderAnalyticsCharts();
        });
      } catch (err) {
        this.showToast(err.message || 'Unable to load analytics.', 'danger');
      }
    },

    /**
     * Approve a company via admin route.
     *
     * @param {number} companyId - Company id.
     * @returns {Promise<void>}
     */
    async approveCompany(companyId) {
      try {
        await this.apiCall('POST', `/api/admin/companies/${companyId}/approve`);
        this.showToast('Company approved.', 'success');
        this.loadAdminCompanies();
      } catch (err) {
        this.showToast(err.message || 'Failed to approve company.', 'danger');
      }
    },

    /**
     * Reject a company with a reason via admin route.
     *
     * @param {number} companyId - Company id.
     * @returns {Promise<void>}
     */
    async rejectCompany(companyId) {
      const reason = window.prompt('Enter rejection reason:');
      if (!reason) return;
      try {
        await this.apiCall('POST', `/api/admin/companies/${companyId}/reject`, { reason });
        this.showToast('Company rejected.', 'success');
        this.loadAdminCompanies();
      } catch (err) {
        this.showToast(err.message || 'Failed to reject company.', 'danger');
      }
    },

    /**
     * Blacklist a company via admin route.
     *
     * @param {number} companyId - Company id.
     * @returns {Promise<void>}
     */
    async toggleBlacklistCompany(company) {
      try {
        if (company.user && company.user.is_blacklisted) {
          if (!window.confirm('Unblacklist this company?')) return;
          await this.apiCall('POST', `/api/admin/companies/${company.id}/unblacklist`);
          this.showToast('Company unblacklisted.', 'success');
        } else {
          if (!window.confirm('Blacklist this company?')) return;
          await this.apiCall('POST', `/api/admin/companies/${company.id}/blacklist`);
          this.showToast('Company blacklisted.', 'success');
        }
        this.loadAdminCompanies();
      } catch (err) {
        this.showToast(err.message || 'Failed to update blacklist status.', 'danger');
      }
    },

    /**
     * Blacklist a student via admin route.
     *
     * @param {number} studentId - Student id.
     * @returns {Promise<void>}
     */
    async blacklistStudent(studentId) {
      if (!window.confirm('Blacklist this student?')) return;
      try {
        await this.apiCall('POST', `/api/admin/students/${studentId}/blacklist`);
        this.showToast('Student blacklisted.', 'success');
        this.loadAdminStudents();
      } catch (err) {
        this.showToast(err.message || 'Failed to blacklist student.', 'danger');
      }
    },

    /**
     * Approve a drive via admin route.
     *
     * @param {number} driveId - Drive id.
     * @returns {Promise<void>}
     */
    async approveDrive(driveId) {
      try {
        await this.apiCall('POST', `/api/admin/drives/${driveId}/approve`);
        this.showToast('Drive approved.', 'success');
        this.loadAdminDrives();
      } catch (err) {
        this.showToast(err.message || 'Failed to approve drive.', 'danger');
      }
    },

    /**
     * Reject a drive with reason via admin route.
     *
     * @param {number} driveId - Drive id.
     * @returns {Promise<void>}
     */
    async rejectDrive(driveId) {
      const reason = window.prompt('Enter rejection reason:');
      if (!reason) return;
      try {
        await this.apiCall('POST', `/api/admin/drives/${driveId}/reject`, { reason });
        this.showToast('Drive rejected.', 'success');
        this.loadAdminDrives();
      } catch (err) {
        this.showToast(err.message || 'Failed to reject drive.', 'danger');
      }
    },

    /**
     * Render admin analytics using Chart.js.
     *
     * @returns {void}
     */
    renderAnalyticsCharts() {
      if (!this.adminAnalytics) return;
      const a = this.adminAnalytics;

      // Drives per month (bar chart).
      const ctx1 = document.getElementById('drivesPerMonthChart');
      if (ctx1) {
        if (this.charts.drivesPerMonth) this.charts.drivesPerMonth.destroy();
        this.charts.drivesPerMonth = new Chart(ctx1, {
          type: 'bar',
          data: {
            labels: a.drives_per_month.map(x => x.month),
            datasets: [
              {
                label: 'Drives',
                data: a.drives_per_month.map(x => x.count),
                backgroundColor: '#0d6efd'
              }
            ]
          },
          options: { responsive: true, maintainAspectRatio: false }
        });
      }

      // Application status breakdown (doughnut).
      const ctx2 = document.getElementById('statusBreakdownChart');
      if (ctx2) {
        if (this.charts.statusBreakdown) this.charts.statusBreakdown.destroy();
        const breakdown = a.application_status_breakdown;
        this.charts.statusBreakdown = new Chart(ctx2, {
          type: 'doughnut',
          data: {
            labels: ['Applied', 'Shortlisted', 'Selected', 'Rejected'],
            datasets: [
              {
                data: [
                  breakdown.applied || 0,
                  breakdown.shortlisted || 0,
                  breakdown.selected || 0,
                  breakdown.rejected || 0
                ],
                backgroundColor: ['#6c757d', '#0dcaf0', '#198754', '#dc3545']
              }
            ]
          },
          options: { responsive: true, maintainAspectRatio: false }
        });
      }

      // Top companies by applicants (horizontal bar).
      const ctx3 = document.getElementById('topCompaniesChart');
      if (ctx3) {
        if (this.charts.topCompanies) this.charts.topCompanies.destroy();
        this.charts.topCompanies = new Chart(ctx3, {
          type: 'bar',
          data: {
            labels: a.top_companies_by_applicants.map(x => x.company),
            datasets: [
              {
                label: 'Applicants',
                data: a.top_companies_by_applicants.map(x => x.applicants),
                backgroundColor: '#6610f2'
              }
            ]
          },
          options: {
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false
          }
        });
      }

      // Monthly selections (line chart).
      const ctx4 = document.getElementById('monthlySelectionsChart');
      if (ctx4) {
        if (this.charts.monthlySelections) this.charts.monthlySelections.destroy();
        this.charts.monthlySelections = new Chart(ctx4, {
          type: 'line',
          data: {
            labels: a.monthly_selections.map(x => x.month),
            datasets: [
              {
                label: 'Selected',
                data: a.monthly_selections.map(x => x.selected),
                borderColor: '#198754',
                fill: false,
                tension: 0.2
              }
            ]
          },
          options: { responsive: true, maintainAspectRatio: false }
        });
      }
    },

    /**
     * Load company dashboard data (profile + drives).
     *
     * @returns {Promise<void>}
     */
    async loadCompanyDashboard() {
      try {
        const res = await this.apiCall('GET', '/api/company/dashboard');
        this.companyProfile = res.data.company_profile;
        this.companyDrives = res.data.drives;
      } catch (err) {
        this.showToast(err.message || 'Unable to load company dashboard.', 'danger');
      }
    },

    /**
     * Load full company profile for edit screen.
     *
     * @returns {Promise<void>}
     */
    async loadCompanyProfile() {
      try {
        const res = await this.apiCall('GET', '/api/company/profile');
        this.companyProfile = res.data.company_profile;
      } catch (err) {
        this.showToast(err.message || 'Unable to load company profile.', 'danger');
      }
    },

    /**
     * Update company profile from bound form.
     *
     * @returns {Promise<void>}
     */
    async submitCompanyProfile() {
      try {
        const res = await this.apiCall('PUT', '/api/company/profile', this.companyProfile);
        this.companyProfile = res.data.company_profile;
        this.showToast('Company profile updated.', 'success');
      } catch (err) {
        this.showToast(err.message || 'Failed to update company profile.', 'danger');
      }
    },

    /**
     * Submit a new placement drive as a company.
     *
     * @returns {Promise<void>}
     */
    async submitCompanyDrive() {
      try {
        const payload = {
          ...this.companyDriveForm,
          eligible_branches: this.companyDriveForm.eligible_branches.join(',')
        };
        const res = await this.apiCall('POST', '/api/company/drives', payload);
        this.showToast('Drive created and submitted for approval.', 'success');
        this.companyDriveForm = {
          job_title: '',
          job_description: '',
          eligible_branches: [],
          min_cgpa: '',
          eligible_passout_year: '',
          package_lpa: '',
          application_deadline: ''
        };
        this.companyDrives.push(res.data.drive);
      } catch (err) {
        this.showToast(err.message || 'Failed to create drive.', 'danger');
      }
    },

    /**
     * Toggle blacklist status for a student (blacklist/unblacklist) as admin.
     *
     * @param {Object} student - Student row object (includes user).
     * @returns {Promise<void>}
     */
    async toggleBlacklistStudent(student) {
      try {
        if (student.user && student.user.is_blacklisted) {
          if (!window.confirm('Unblacklist this student?')) return;
          await this.apiCall('POST', `/api/admin/students/${student.id}/unblacklist`);
          this.showToast('Student unblacklisted.', 'success');
        } else {
          if (!window.confirm('Blacklist this student?')) return;
          await this.apiCall('POST', `/api/admin/students/${student.id}/blacklist`);
          this.showToast('Student blacklisted.', 'success');
        }
        this.loadAdminStudents();
      } catch (err) {
        this.showToast(err.message || 'Failed to update student blacklist status.', 'danger');
      }
    },

    /**
     * Load applications for a specific company drive.
     *
     * @param {number} driveId - Drive id.
     * @returns {Promise<void>}
     */
    async loadCompanyDriveApplications(driveId) {
      try {
        this.companySelectedDriveId = driveId ? Number(driveId) : null;
        const res = await this.apiCall('GET', `/api/company/drives/${driveId}/applications`);
        this.companyDriveApplications = res.data.applications;
      } catch (err) {
        this.showToast(err.message || 'Failed to load applications.', 'danger');
      }
    },

    /**
     * Shortlist an application as company.
     *
     * @param {number} applicationId - Application id.
     * @returns {Promise<void>}
     */
    async shortlistApplication(applicationId) {
      try {
        await this.apiCall('POST', `/api/company/applications/${applicationId}/shortlist`);
        const row = this.companyDriveApplications.find(x => x.id === applicationId);
        if (row) row.status = 'shortlisted';
        this.showToast('Application shortlisted.', 'success');
        if (this.companySelectedDriveId) this.loadCompanyDriveApplications(this.companySelectedDriveId);
      } catch (err) {
        this.showToast(err.message || 'Failed to shortlist application.', 'danger');
      }
    },

    /**
     * Mark an application selected as company.
     *
     * @param {number} applicationId - Application id.
     * @returns {Promise<void>}
     */
    async selectApplication(applicationId) {
      try {
        await this.apiCall('POST', `/api/company/applications/${applicationId}/select`);
        const row = this.companyDriveApplications.find(x => x.id === applicationId);
        if (row) row.status = 'selected';
        this.showToast('Application selected.', 'success');
        if (this.companySelectedDriveId) this.loadCompanyDriveApplications(this.companySelectedDriveId);
      } catch (err) {
        this.showToast(err.message || 'Failed to select application.', 'danger');
      }
    },

    /**
     * Reject an application as company.
     *
     * @param {number} applicationId - Application id.
     * @returns {Promise<void>}
     */
    async rejectApplication(applicationId) {
      try {
        await this.apiCall('POST', `/api/company/applications/${applicationId}/reject`);
        const row = this.companyDriveApplications.find(x => x.id === applicationId);
        if (row) row.status = 'rejected';
        this.showToast('Application rejected.', 'success');
        if (this.companySelectedDriveId) this.loadCompanyDriveApplications(this.companySelectedDriveId);
      } catch (err) {
        this.showToast(err.message || 'Failed to reject application.', 'danger');
      }
    },

    /**
     * Load student dashboard drives according to filters.
     *
     * @returns {Promise<void>}
     */
    async loadStudentDashboard() {
      try {
        const params = new URLSearchParams();
        Object.entries(this.studentDashboardFilters).forEach(([k, v]) => {
          if (v) params.append(k, v);
        });
        const query = params.toString() ? `?${params.toString()}` : '';
        const res = await this.apiCall('GET', `/api/student/dashboard${query}`);
        this.studentDashboardDrives = res.data.drives;
      } catch (err) {
        this.showToast(err.message || 'Unable to load student dashboard.', 'danger');
      }
    },

    /**
     * Load full drive details for student and navigate to detail view.
     *
     * @param {number} driveId - Drive id.
     * @returns {Promise<void>}
     */
    async loadStudentDriveDetails(driveId) {
      try {
        const res = await this.apiCall('GET', `/api/student/drives/${driveId}`);
        this.studentSelectedDrive = res.data.drive;
        this.navigateTo('studentDriveDetails');
      } catch (err) {
        this.showToast(err.message || 'Unable to load drive details.', 'danger');
      }
    },

    /**
     * Load student profile.
     *
     * @returns {Promise<void>}
     */
    async loadStudentProfile() {
      try {
        const res = await this.apiCall('GET', '/api/student/profile');
        this.studentProfile = res.data.student_profile;
      } catch (err) {
        this.showToast(err.message || 'Unable to load student profile.', 'danger');
      }
    },

    /**
     * Save updated student profile.
     *
     * @returns {Promise<void>}
     */
    async submitStudentProfile() {
      try {
        const payload = { ...this.studentProfile };
        delete payload.user_id;
        // Send year_of_passout (backend accepts it and stores in year_of_study column).
        if (payload.year_of_passout !== undefined) {
          payload.year_of_passout = Number(payload.year_of_passout);
        }
        const res = await this.apiCall('PUT', '/api/student/profile', payload);
        this.studentProfile = res.data.student_profile;
        this.showToast('Student profile updated.', 'success');
      } catch (err) {
        this.showToast(err.message || 'Failed to update student profile.', 'danger');
      }
    },

    /**
     * Upload a resume file for the student profile.
     *
     * @param {Event} event - File input change event.
     * @returns {Promise<void>}
     */
    async uploadResume(event) {
      try {
        const file = event.target.files[0];
        if (!file) return;
        const formData = new FormData();
        formData.append('resume', file);
        const res = await this.apiCall('POST', '/api/student/profile/resume', formData, true);
        if (this.studentProfile) {
          this.studentProfile.resume_path = res.data.resume_url;
        }
        this.showToast('Resume uploaded.', 'success');
      } catch (err) {
        this.showToast(err.message || 'Failed to upload resume.', 'danger');
      }
    },

    /**
     * Apply to a placement drive as student.
     *
     * @param {number} driveId - Drive id.
     * @returns {Promise<void>}
     */
    async applyToDrive(driveId) {
      try {
        await this.apiCall('POST', `/api/student/drives/${driveId}/apply`);
        this.showToast('Applied successfully.', 'success');
        this.loadStudentApplications();
        // Refresh dashboard + details state so buttons update instantly.
        if (this.currentPage === 'studentDashboard') {
          this.loadStudentDashboard();
        }
        if (this.currentPage === 'studentDriveDetails' && this.studentSelectedDrive && this.studentSelectedDrive.id === driveId) {
          this.loadStudentDriveDetails(driveId);
        }
      } catch (err) {
        this.showToast(err.message || 'Failed to apply.', 'danger');
      }
    },

    /**
     * Load all applications for the logged-in student.
     *
     * @returns {Promise<void>}
     */
    async loadStudentApplications() {
      try {
        const res = await this.apiCall('GET', '/api/student/applications');
        this.studentApplications = res.data.applications;
      } catch (err) {
        this.showToast(err.message || 'Unable to load applications.', 'danger');
      }
    },

    /**
     * View offer letter for an application in a new tab.
     *
     * @param {number} applicationId
     * @returns {Promise<void>}
     */
    async viewOfferLetter(applicationId) {
      try {
        await this.openProtectedFile(`/api/student/applications/${applicationId}/offer-letter`, 'text/html');
      } catch (err) {
        this.showToast(err.message || 'Unable to open offer letter.', 'danger');
      }
    },

    /**
     * View current student's resume in a new tab.
     *
     * @returns {Promise<void>}
     */
    async viewCurrentResume() {
      try {
        const url = this.studentProfile && (this.studentProfile.resume_url || this.studentProfile.resume_path);
        if (!url) {
          this.showToast('No resume uploaded yet.', 'danger');
          return;
        }
        await this.openProtectedFile(url, 'application/pdf');
      } catch (err) {
        this.showToast(err.message || 'Unable to open resume.', 'danger');
      }
    },

    /**
     * Company: open a student's resume for an application.
     *
     * @param {number} applicationId
     * @returns {Promise<void>}
     */
    async viewStudentResumeForApplication(applicationId) {
      try {
        await this.openProtectedFile(`/api/company/applications/${applicationId}/resume`, 'application/pdf');
      } catch (err) {
        this.showToast(err.message || 'Unable to open student resume.', 'danger');
      }
    },

    /**
     * Trigger CSV export of applications and start polling for status.
     *
     * @returns {Promise<void>}
     */
    async startExport() {
      try {
        const res = await this.apiCall('POST', '/api/student/export');
        const jobId = res.data.export_job_id;
        this.showToast('Export started.', 'success');
        this.pollExportStatus(jobId);
      } catch (err) {
        this.showToast(err.message || 'Failed to start export.', 'danger');
      }
    },

    /**
     * Poll export job status until file is ready or failed.
     *
     * @param {number} jobId - ExportJob id.
     * @returns {void}
     */
    pollExportStatus(jobId) {
      if (this.exportJobPollingId) {
        clearInterval(this.exportJobPollingId);
      }
      this.exportJobPollingId = setInterval(async () => {
        try {
          const res = await this.apiCall('GET', `/api/student/export/${jobId}/status`);
          const job = res.data.export_job;
          if (job.status === 'done') {
            clearInterval(this.exportJobPollingId);
            this.exportJobPollingId = null;
            await this.downloadProtectedFile(`/api/student/export/${jobId}/download`, `applications_${jobId}.csv`);
          } else if (job.status === 'failed') {
            clearInterval(this.exportJobPollingId);
            this.exportJobPollingId = null;
            this.showToast('Export failed.', 'danger');
          }
        } catch (err) {
          clearInterval(this.exportJobPollingId);
          this.exportJobPollingId = null;
          this.showToast(err.message || 'Export polling error.', 'danger');
        }
      }, 3000);
    }
  },

  /**
   * Mounted hook: attempt to restore session and route appropriately.
   *
   * @returns {Promise<void>}
   */
  async mounted() {
    if (this.token) {
      await this.loadCurrentUser();
      if (this.currentUser) {
        this.navigateAfterLogin();
      }
    }
  },

  watch: {
    /**
     * Live filtering on student dashboard: whenever any filter changes,
     * reload drives with a small debounce to avoid spamming the API.
     */
    studentDashboardFilters: {
      deep: true,
      handler() {
        if (!this.isStudent || this.currentPage !== 'studentDashboard') {
          return;
        }
        if (this.studentFilterDebounceId) {
          clearTimeout(this.studentFilterDebounceId);
        }
        this.studentFilterDebounceId = setTimeout(() => {
          this.loadStudentDashboard();
        }, 300);
      }
    }
  },

  /**
   * Render function using template string for the entire SPA.
   */
  template: `
    <div>
      <nav class="navbar navbar-expand-lg navbar-dark bg-primary mb-3">
        <div class="container-fluid">
          <a class="navbar-brand fw-bold" href="javascript:void(0);" @click="currentUser ? navigateAfterLogin() : navigateTo('login')">
            IIT Madras Placement Portal
          </a>
          <button
            class="navbar-toggler"
            type="button"
            data-bs-toggle="collapse"
            data-bs-target="#navbarNav"
          >
            <span class="navbar-toggler-icon"></span>
          </button>
          <div class="collapse navbar-collapse" id="navbarNav">
            <ul class="navbar-nav me-auto mb-2 mb-lg-0" v-if="currentUser">
              <li class="nav-item" v-if="isAdmin">
                <a class="nav-link" :class="{ active: currentPage === 'adminDashboard' }" href="javascript:void(0);" @click="navigateTo('adminDashboard'); loadAdminDashboard();">
                  Dashboard
                </a>
              </li>
              <li class="nav-item" v-if="isAdmin">
                <a class="nav-link" :class="{ active: currentPage === 'adminCompanies' }" href="javascript:void(0);" @click="navigateTo('adminCompanies'); loadAdminCompanies();">
                  Companies
                </a>
              </li>
              <li class="nav-item" v-if="isAdmin">
                <a class="nav-link" :class="{ active: currentPage === 'adminStudents' }" href="javascript:void(0);" @click="navigateTo('adminStudents'); loadAdminStudents();">
                  Students
                </a>
              </li>
              <li class="nav-item" v-if="isAdmin">
                <a class="nav-link" :class="{ active: currentPage === 'adminDrives' }" href="javascript:void(0);" @click="navigateTo('adminDrives'); loadAdminDrives();">
                  Drives
                </a>
              </li>
              <li class="nav-item" v-if="isAdmin">
                <a class="nav-link" :class="{ active: currentPage === 'adminApplications' }" href="javascript:void(0);" @click="navigateTo('adminApplications'); loadAdminApplications();">
                  Applications
                </a>
              </li>
              <li class="nav-item" v-if="isAdmin">
                <a class="nav-link" :class="{ active: currentPage === 'adminAnalytics' }" href="javascript:void(0);" @click="navigateTo('adminAnalytics'); loadAdminAnalytics();">
                  Analytics
                </a>
              </li>

              <li class="nav-item" v-if="isCompany">
                <a class="nav-link" :class="{ active: currentPage === 'companyDashboard' }" href="javascript:void(0);" @click="navigateTo('companyDashboard'); loadCompanyDashboard();">
                  Dashboard
                </a>
              </li>
              <li class="nav-item" v-if="isCompany">
                <a class="nav-link" :class="{ active: currentPage === 'companyCreateDrive' }" href="javascript:void(0);" @click="navigateTo('companyCreateDrive');">
                  Create Drive
                </a>
              </li>
              <li class="nav-item" v-if="isCompany">
                <a class="nav-link" :class="{ active: currentPage === 'companyDriveApplications' }" href="javascript:void(0);" @click="navigateTo('companyDriveApplications');">
                  Drive Applications
                </a>
              </li>

              <li class="nav-item" v-if="isStudent">
                <a class="nav-link" :class="{ active: currentPage === 'studentDashboard' }" href="javascript:void(0);" @click="navigateTo('studentDashboard'); loadStudentDashboard();">
                  Dashboard
                </a>
              </li>
              <li class="nav-item" v-if="isStudent">
                <a class="nav-link" :class="{ active: currentPage === 'studentProfile' }" href="javascript:void(0);" @click="navigateTo('studentProfile'); loadStudentProfile();">
                  Profile
                </a>
              </li>
              <li class="nav-item" v-if="isStudent">
                <a class="nav-link" :class="{ active: currentPage === 'studentApplications' }" href="javascript:void(0);" @click="navigateTo('studentApplications'); loadStudentApplications();">
                  Applications
                </a>
              </li>
            </ul>
            <div class="d-flex align-items-center">
              <span v-if="currentUser" class="navbar-text me-3">
                {{ currentUser.name }} ({{ currentUser.role }})
              </span>
              <button v-if="currentUser" class="btn btn-outline-light btn-sm" @click="logout">
                Logout
              </button>
            </div>
          </div>
        </div>
      </nav>

      <div class="container mb-5">
        <div v-if="toast.show" class="position-fixed top-0 end-0 p-3" style="z-index: 1080;">
          <div class="toast show" :class="toast.type === 'success' ? 'text-bg-success' : 'text-bg-danger'">
            <div class="toast-body">
              {{ toast.message }}
            </div>
          </div>
        </div>

        <div v-if="isLoading" class="position-fixed top-0 start-0 w-100 h-100 d-flex justify-content-center align-items-center bg-dark bg-opacity-25" style="z-index: 1070;">
          <div class="spinner-border text-primary" role="status">
            <span class="visually-hidden">Loading...</span>
          </div>
        </div>

        <!-- Public Pages -->
        <div v-if="!currentUser">
          <div v-if="currentPage === 'login'" class="row justify-content-center">
            <div class="col-md-5">
              <div class="card shadow-sm">
                <div class="card-body">
                  <h5 class="card-title mb-3">Login</h5>
                  <div class="mb-3">
                    <label class="form-label">Email</label>
                    <input v-model="loginForm.email" type="email" class="form-control" />
                  </div>
                  <div class="mb-3">
                    <label class="form-label">Password</label>
                    <input v-model="loginForm.password" type="password" class="form-control" />
                  </div>
                  <button class="btn btn-primary w-100 mb-2" @click="submitLogin" :disabled="isLoading">
                    Login
                  </button>
                  <div class="d-flex justify-content-between">
                    <button class="btn btn-link p-0" @click="navigateTo('studentRegister')">Student Registration</button>
                    <button class="btn btn-link p-0" @click="navigateTo('companyRegister')">Company Registration</button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div v-if="currentPage === 'studentRegister'" class="row justify-content-center">
            <div class="col-md-7">
              <div class="card shadow-sm">
                <div class="card-body">
                  <h5 class="card-title mb-3">Student Registration</h5>
                  <div class="row g-3">
                    <div class="col-md-6">
                      <label class="form-label">Email</label>
                      <input v-model="studentRegisterForm.email" type="email" class="form-control" />
                    </div>
                    <div class="col-md-6">
                      <label class="form-label">Password</label>
                      <input v-model="studentRegisterForm.password" type="password" class="form-control" />
                    </div>
                    <div class="col-md-6">
                      <label class="form-label">Full Name</label>
                      <input v-model="studentRegisterForm.full_name" type="text" class="form-control" />
                    </div>
                    <div class="col-md-6">
                      <label class="form-label">Roll Number</label>
                      <input v-model="studentRegisterForm.roll_number" type="text" class="form-control" />
                    </div>
                    <div class="col-md-4">
                      <label class="form-label">Branch</label>
                      <select v-model="studentRegisterForm.branch" class="form-select">
                        <option disabled value="">Select branch</option>
                        <option value="CSE">CSE</option>
                        <option value="ECE">ECE</option>
                        <option value="EE">EE</option>
                        <option value="ME">ME</option>
                      </select>
                    </div>
                    <div class="col-md-4">
                      <label class="form-label">Year of Passout</label>
                      <input v-model="studentRegisterForm.year_of_passout" type="number" min="2000" max="2100" class="form-control" />
                    </div>
                    <div class="col-md-4">
                      <label class="form-label">CGPA</label>
                      <input v-model="studentRegisterForm.cgpa" type="number" step="0.1" class="form-control" />
                    </div>
                    <div class="col-md-6">
                      <label class="form-label">Phone (10 digits)</label>
                      <input v-model="studentRegisterForm.phone" type="text" inputmode="numeric" maxlength="10" class="form-control" placeholder="10-digit mobile number" />
                    </div>
                  <div class="col-md-6">
                    <label class="form-label">Resume (PDF / DOC / DOCX)</label>
                    <input
                      type="file"
                      class="form-control"
                      accept=".pdf,.doc,.docx"
                      @change="onStudentRegisterResumeChange"
                    />
                    <small class="text-muted">Uploading a resume is mandatory for registration.</small>
                  </div>
                  </div>
                  <div class="mt-3 d-flex justify-content-between">
                    <button class="btn btn-secondary" @click="navigateTo('login')">Back to Login</button>
                    <button class="btn btn-primary" @click="submitStudentRegister" :disabled="isLoading">Register</button>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div v-if="currentPage === 'companyRegister'" class="row justify-content-center">
            <div class="col-md-7">
              <div class="card shadow-sm">
                <div class="card-body">
                  <h5 class="card-title mb-3">Company Registration</h5>
                  <div class="row g-3">
                    <div class="col-md-6">
                      <label class="form-label">Email</label>
                      <input v-model="companyRegisterForm.email" type="email" class="form-control" />
                    </div>
                    <div class="col-md-6">
                      <label class="form-label">Password</label>
                      <input v-model="companyRegisterForm.password" type="password" class="form-control" />
                    </div>
                    <div class="col-md-6">
                      <label class="form-label">Company Name</label>
                      <input v-model="companyRegisterForm.company_name" type="text" class="form-control" />
                    </div>
                    <div class="col-md-6">
                      <label class="form-label">HR Name</label>
                      <input v-model="companyRegisterForm.hr_name" type="text" class="form-control" />
                    </div>
                    <div class="col-md-6">
                      <label class="form-label">HR Email</label>
                      <input v-model="companyRegisterForm.hr_email" type="email" class="form-control" />
                    </div>
                    <div class="col-md-6">
                      <label class="form-label">Website</label>
                      <input v-model="companyRegisterForm.website" type="text" class="form-control" />
                    </div>
                    <div class="col-12">
                      <label class="form-label">Description</label>
                      <textarea v-model="companyRegisterForm.description" rows="3" class="form-control"></textarea>
                    </div>
                  </div>
                  <div class="mt-3 d-flex justify-content-between">
                    <button class="btn btn-secondary" @click="navigateTo('login')">Back to Login</button>
                    <button class="btn btn-primary" @click="submitCompanyRegister" :disabled="isLoading">Register</button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Admin Pages -->
        <div v-if="currentUser && isAdmin">
          <div v-if="currentPage === 'adminDashboard'">
            <h4 class="mb-3">Admin Dashboard</h4>
            <div v-if="adminDashboard" class="row g-3 mb-3">
              <div class="col-md-3">
                <div class="card text-bg-primary">
                  <div class="card-body">
                    <div class="card-title">Students</div>
                    <div class="fs-3 fw-bold">{{ adminDashboard.total_students }}</div>
                  </div>
                </div>
              </div>
              <div class="col-md-3">
                <div class="card text-bg-success">
                  <div class="card-body">
                    <div class="card-title">Companies</div>
                    <div class="fs-3 fw-bold">{{ adminDashboard.total_companies }}</div>
                  </div>
                </div>
              </div>
              <div class="col-md-3">
                <div class="card text-bg-info">
                  <div class="card-body">
                    <div class="card-title">Drives</div>
                    <div class="fs-3 fw-bold">{{ adminDashboard.total_drives }}</div>
                  </div>
                </div>
              </div>
              <div class="col-md-3">
                <div class="card text-bg-secondary">
                  <div class="card-body">
                    <div class="card-title">Applications</div>
                    <div class="fs-3 fw-bold">{{ adminDashboard.total_applications }}</div>
                  </div>
                </div>
              </div>
            </div>
            <div class="row g-3">
              <div class="col-md-6">
                <div class="card">
                  <div class="card-header fw-semibold">Recent Drives</div>
                  <div class="card-body p-0">
                    <table class="table table-hover table-striped table-responsive mb-0">
                      <thead>
                        <tr>
                          <th>Job Title</th>
                          <th>Company</th>
                          <th>Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-if="!adminDashboard || !adminDashboard.recent_drives.length">
                          <td colspan="3" class="text-center text-muted">No recent drives.</td>
                        </tr>
                        <tr v-for="d in adminDashboard?.recent_drives || []" :key="d.id">
                          <td>{{ d.job_title }}</td>
                          <td>{{ d.company?.company_name }}</td>
                          <td>
                            <span class="badge"
                              :class="{
                                'bg-warning text-dark': d.status === 'pending',
                                'bg-success': d.status === 'approved',
                                'bg-danger': d.status === 'rejected'
                              }"
                            >
                              {{ d.status }}
                            </span>
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
              <div class="col-md-6">
                <div class="card">
                  <div class="card-header fw-semibold">Recent Applications</div>
                  <div class="card-body p-0">
                    <table class="table table-hover table-striped table-responsive mb-0">
                      <thead>
                        <tr>
                          <th>Student</th>
                          <th>Job</th>
                          <th>Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-if="!adminDashboard || !adminDashboard.recent_applications.length">
                          <td colspan="3" class="text-center text-muted">No recent applications.</td>
                        </tr>
                        <tr v-for="a in adminDashboard?.recent_applications || []" :key="a.id">
                          <td>{{ a.student?.full_name }}</td>
                          <td>{{ a.drive?.job_title }}</td>
                          <td>
                            <span class="badge"
                              :class="{
                                'bg-secondary': a.status === 'applied',
                                'bg-info text-dark': a.status === 'shortlisted',
                                'bg-success': a.status === 'selected',
                                'bg-danger': a.status === 'rejected'
                              }"
                            >
                              {{ a.status }}
                            </span>
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div v-if="currentPage === 'adminCompanies'">
            <div class="d-flex justify-content-between align-items-center mb-3">
              <h4 class="mb-0">Companies</h4>
              <div class="d-flex">
                <input v-model="adminCompaniesSearch" type="text" class="form-control form-control-sm me-2" placeholder="Search companies..." />
                <button class="btn btn-sm btn-outline-primary" @click="loadAdminCompanies">Search</button>
              </div>
            </div>
            <table class="table table-hover table-striped table-responsive">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>HR</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="!adminCompanies.length">
                  <td colspan="4" class="text-center text-muted">No companies found.</td>
                </tr>
                <tr v-for="c in adminCompanies" :key="c.id">
                  <td>{{ c.company_name }}</td>
                  <td>{{ c.hr_name }}</td>
                  <td>
                    <span class="badge"
                      :class="{
                        'bg-warning text-dark': c.approval_status === 'pending',
                        'bg-success': c.approval_status === 'approved',
                        'bg-danger': c.approval_status === 'rejected'
                      }"
                    >
                      {{ c.approval_status }}
                    </span>
                  </td>
                  <td>
                    <button
                      class="btn btn-sm btn-success me-1"
                      @click="approveCompany(c.id)"
                      :disabled="isLoading || c.approval_status !== 'pending' || (c.user && c.user.is_blacklisted)"
                    >
                      Approve
                    </button>
                    <button
                      class="btn btn-sm btn-danger me-1"
                      @click="rejectCompany(c.id)"
                      :disabled="isLoading || c.approval_status !== 'pending' || (c.user && c.user.is_blacklisted)"
                    >
                      Reject
                    </button>
                    <button
                      class="btn btn-sm btn-outline-danger"
                      @click="toggleBlacklistCompany(c)"
                      :disabled="isLoading"
                    >
                      {{ c.user && c.user.is_blacklisted ? 'Unblacklist' : 'Blacklist' }}
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div v-if="currentPage === 'adminStudents'">
            <div class="d-flex justify-content-between align-items-center mb-3">
              <h4 class="mb-0">Students</h4>
              <div class="d-flex">
                <input v-model="adminStudentsSearch" type="text" class="form-control form-control-sm me-2" placeholder="Search students..." />
                <button class="btn btn-sm btn-outline-primary" @click="loadAdminStudents">Search</button>
              </div>
            </div>
            <table class="table table-hover table-striped table-responsive">
              <thead>
                <tr>
                  <th>Name</th>
                  <th>Roll</th>
                  <th>Branch</th>
                  <th>CGPA</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="!adminStudents.length">
                  <td colspan="5" class="text-center text-muted">No students found.</td>
                </tr>
                <tr v-for="s in adminStudents" :key="s.id">
                  <td>{{ s.full_name }}</td>
                  <td>{{ s.roll_number }}</td>
                  <td>{{ s.branch }}</td>
                  <td>{{ s.cgpa }}</td>
                  <td class="d-flex gap-2">
                    <button
                      class="btn btn-sm btn-outline-danger"
                      @click="toggleBlacklistStudent(s)"
                      :disabled="isLoading || (s.user && s.user.is_blacklisted)"
                    >
                      Blacklist
                    </button>
                    <button
                      class="btn btn-sm btn-outline-secondary"
                      @click="toggleBlacklistStudent(s)"
                      :disabled="isLoading || !(s.user && s.user.is_blacklisted)"
                    >
                      Unblacklist
                    </button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div v-if="currentPage === 'adminDrives'">
            <h4 class="mb-3">Drives</h4>
            <table class="table table-hover table-striped table-responsive">
              <thead>
                <tr>
                  <th>Job Title</th>
                  <th>Company</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="!adminDrives.length">
                  <td colspan="4" class="text-center text-muted">No drives found.</td>
                </tr>
                <tr v-for="d in adminDrives" :key="d.id">
                  <td>{{ d.job_title }}</td>
                  <td>{{ d.company?.company_name }}</td>
                  <td>
                    <span class="badge"
                      :class="{
                        'bg-warning text-dark': d.status === 'pending',
                        'bg-success': d.status === 'approved',
                        'bg-danger': d.status === 'rejected'
                      }"
                    >
                      {{ d.status }}
                    </span>
                  </td>
                  <td>
                    <button class="btn btn-sm btn-success me-1" @click="approveDrive(d.id)" :disabled="isLoading || d.status !== 'pending'">Approve</button>
                    <button class="btn btn-sm btn-danger" @click="rejectDrive(d.id)" :disabled="isLoading || d.status !== 'pending'">Reject</button>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div v-if="currentPage === 'adminApplications'">
            <h4 class="mb-3">Applications</h4>
            <table class="table table-hover table-striped table-responsive">
              <thead>
                <tr>
                  <th>Student</th>
                  <th>Company</th>
                  <th>Job</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="!adminApplications.length">
                  <td colspan="4" class="text-center text-muted">No applications found.</td>
                </tr>
                <tr v-for="a in adminApplications" :key="a.id">
                  <td>{{ a.student?.full_name }}</td>
                  <td>{{ a.drive?.company?.company_name }}</td>
                  <td>{{ a.drive?.job_title }}</td>
                  <td>
                    <span class="badge"
                      :class="{
                        'bg-secondary': a.status === 'applied',
                        'bg-info text-dark': a.status === 'shortlisted',
                        'bg-success': a.status === 'selected',
                        'bg-danger': a.status === 'rejected'
                      }"
                    >
                      {{ a.status }}
                    </span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>

          <div v-if="currentPage === 'adminAnalytics'">
            <h4 class="mb-3">Analytics</h4>
            <div class="row g-3">
              <div class="col-md-6" style="height:420px;">
                <div class="card h-100">
                  <div class="card-header fw-semibold">Drives per Month</div>
                  <div class="card-body" style="height:calc(100% - 48px);">
                    <canvas id="drivesPerMonthChart" style="width:100%;height:100%;"></canvas>
                  </div>
                </div>
              </div>
              <div class="col-md-6" style="height:420px;">
                <div class="card h-100">
                  <div class="card-header fw-semibold">Application Status Breakdown</div>
                  <div class="card-body" style="height:calc(100% - 48px);">
                    <canvas id="statusBreakdownChart" style="width:100%;height:100%;"></canvas>
                  </div>
                </div>
              </div>
              <div class="col-md-6" style="height:420px;">
                <div class="card h-100">
                  <div class="card-header fw-semibold">Top Companies by Applicants</div>
                  <div class="card-body" style="height:calc(100% - 48px);">
                    <canvas id="topCompaniesChart" style="width:100%;height:100%;"></canvas>
                  </div>
                </div>
              </div>
              <div class="col-md-6" style="height:420px;">
                <div class="card h-100">
                  <div class="card-header fw-semibold">Monthly Selections</div>
                  <div class="card-body" style="height:calc(100% - 48px);">
                    <canvas id="monthlySelectionsChart" style="width:100%;height:100%;"></canvas>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Company Pages -->
        <div v-if="currentUser && isCompany">
          <div v-if="currentPage === 'companyDashboard'">
            <h4 class="mb-3">Company Dashboard</h4>
            <div v-if="companyProfile" class="alert" :class="{
              'alert-warning': companyProfile.approval_status === 'pending',
              'alert-success': companyProfile.approval_status === 'approved',
              'alert-danger': companyProfile.approval_status === 'rejected'
            }">
              <strong>Status:</strong> {{ companyProfile.approval_status }}
              <span v-if="companyProfile.approval_status === 'rejected' && companyProfile.rejection_reason">
                — {{ companyProfile.rejection_reason }}
              </span>
            </div>
            <div class="row g-3">
              <div class="col-md-4" v-if="companyProfile">
                <div class="card h-100">
                  <div class="card-body">
                    <h5 class="card-title">{{ companyProfile.company_name }}</h5>
                    <p class="mb-1"><strong>HR:</strong> {{ companyProfile.hr_name }}</p>
                    <p class="mb-1"><strong>Email:</strong> {{ companyProfile.hr_email }}</p>
                    <p class="mb-1" v-if="companyProfile.website"><strong>Website:</strong> {{ companyProfile.website }}</p>
                    <p class="mt-2 text-muted" v-if="companyProfile.description">{{ companyProfile.description }}</p>
                  </div>
                </div>
              </div>
              <div class="col-md-8">
                <div class="card h-100">
                  <div class="card-header fw-semibold">Drives</div>
                  <div class="card-body p-0">
                    <table class="table table-hover table-striped table-responsive mb-0">
                      <thead>
                        <tr>
                          <th>Job Title</th>
                          <th>Status</th>
                          <th>Applicants</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr v-if="!companyDrives.length">
                          <td colspan="3" class="text-center text-muted">No drives created yet.</td>
                        </tr>
                        <tr v-for="d in companyDrives" :key="d.id">
                          <td>{{ d.job_title }}</td>
                          <td>
                            <span class="badge"
                              :class="{
                                'bg-warning text-dark': d.status === 'pending',
                                'bg-success': d.status === 'approved',
                                'bg-danger': d.status === 'rejected'
                              }"
                            >
                              {{ d.status }}
                            </span>
                          </td>
                          <td>{{ d.applicant_count || 0 }}</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div v-if="currentPage === 'companyCreateDrive'">
            <h4 class="mb-3">Create Placement Drive</h4>
            <div class="card">
              <div class="card-body">
                <div class="row g-3">
                  <div class="col-md-6">
                    <label class="form-label">Job Title</label>
                    <input v-model="companyDriveForm.job_title" type="text" class="form-control" />
                  </div>
                  <div class="col-md-6">
                    <label class="form-label">Application Deadline</label>
                    <input v-model="companyDriveForm.application_deadline" type="datetime-local" class="form-control" />
                  </div>
                  <div class="col-md-12">
                    <label class="form-label">Job Description</label>
                    <textarea v-model="companyDriveForm.job_description" rows="4" class="form-control"></textarea>
                  </div>
                  <div class="col-md-6">
                    <label class="form-label">Eligible Branches</label>
                    <div class="d-flex flex-wrap">
                      <div class="form-check me-3" v-for="b in companyBranches" :key="b">
                        <input class="form-check-input" type="checkbox" :id="'branch-' + b"
                          :value="b"
                          v-model="companyDriveForm.eligible_branches" />
                        <label class="form-check-label" :for="'branch-' + b">{{ b }}</label>
                      </div>
                    </div>
                  </div>
                  <div class="col-md-2">
                    <label class="form-label">Min CGPA</label>
                    <input v-model="companyDriveForm.min_cgpa" type="number" step="0.1" class="form-control" />
                  </div>
                  <div class="col-md-2">
                    <label class="form-label">Eligible Passout Year</label>
                    <input v-model="companyDriveForm.eligible_passout_year" type="number" min="2000" max="2100" class="form-control" />
                  </div>
                  <div class="col-md-2">
                    <label class="form-label">Package (LPA)</label>
                    <input v-model="companyDriveForm.package_lpa" type="number" step="0.1" class="form-control" />
                  </div>
                </div>
                <div class="mt-3 text-end">
                  <button class="btn btn-primary" @click="submitCompanyDrive">Create Drive</button>
                </div>
              </div>
            </div>
          </div>

          <div v-if="currentPage === 'companyDriveApplications'">
            <h4 class="mb-3">Drive Applications</h4>
            <div v-if="!companyDrives.length" class="alert alert-info">
              No drives created yet. Create a drive first.
            </div>
            <div v-else>
              <div class="mb-2">
                <label class="form-label">Select Drive</label>
                <select class="form-select" @change="loadCompanyDriveApplications($event.target.value)">
                  <option value="">-- Select --</option>
                  <option v-for="d in companyDrives" :key="d.id" :value="d.id">
                    {{ d.job_title }} ({{ d.status }})
                  </option>
                </select>
              </div>
              <table class="table table-hover table-striped table-responsive mt-3">
                <thead>
                  <tr>
                    <th>Student</th>
                    <th>Roll</th>
                    <th>Branch</th>
                    <th>CGPA</th>
                    <th>Resume</th>
                    <th>Status</th>
                    <th>Actions</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-if="!companyDriveApplications.length">
                    <td colspan="7" class="text-center text-muted">No applications.</td>
                  </tr>
                  <tr v-for="a in companyDriveApplications" :key="a.id">
                    <td>{{ a.student.full_name }}</td>
                    <td>{{ a.student.roll_number }}</td>
                    <td>{{ a.student.branch }}</td>
                    <td>{{ a.student.cgpa }}</td>
                    <td>
                      <button
                        v-if="a.student && a.student.resume_url"
                        class="btn btn-sm btn-outline-primary"
                        @click="viewStudentResumeForApplication(a.id)"
                      >
                        Open
                      </button>
                      <span v-else class="text-muted">N/A</span>
                    </td>
                    <td>
                      <span class="badge"
                        :class="{
                          'bg-secondary': a.status === 'applied',
                          'bg-info text-dark': a.status === 'shortlisted',
                          'bg-success': a.status === 'selected',
                          'bg-danger': a.status === 'rejected'
                        }"
                      >
                        {{ a.status }}
                      </span>
                    </td>
                    <td>
                      <button
                        class="btn btn-sm btn-info me-1"
                        @click="shortlistApplication(a.id)"
                        :disabled="isLoading || a.status !== 'applied'"
                      >
                        Shortlist
                      </button>
                      <button
                        class="btn btn-sm btn-success me-1"
                        @click="selectApplication(a.id)"
                        :disabled="isLoading || a.status !== 'shortlisted'"
                      >
                        Select
                      </button>
                      <button
                        class="btn btn-sm btn-danger"
                        @click="rejectApplication(a.id)"
                        :disabled="isLoading || a.status !== 'shortlisted'"
                      >
                        Reject
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
        </div>

        <!-- Student Pages -->
        <div v-if="currentUser && isStudent">
          <div v-if="currentPage === 'studentDashboard'">
            <h4 class="mb-3">Student Dashboard</h4>
            <div class="card mb-3">
              <div class="card-body">
                <div class="row g-3">
                  <div class="col-md-3">
                    <label class="form-label">Search</label>
                    <input v-model="studentDashboardFilters.search" type="text" class="form-control" placeholder="Job title..." />
                  </div>
                  <div class="col-md-3">
                    <label class="form-label">Branch</label>
                    <input v-model="studentDashboardFilters.branch" type="text" class="form-control" />
                  </div>
                  <div class="col-md-3">
                    <label class="form-label">Min CGPA</label>
                    <input v-model="studentDashboardFilters.min_cgpa" type="number" step="0.1" class="form-control" />
                  </div>
                  <div class="col-md-3">
                    <label class="form-label">Passout Year</label>
                    <input v-model="studentDashboardFilters.year" type="number" min="2000" max="2100" class="form-control" />
                  </div>
                </div>
                <div class="mt-3 text-end">
                  <button class="btn btn-sm btn-outline-primary" @click="loadStudentDashboard">Apply Filters</button>
                </div>
              </div>
            </div>

            <div class="row g-3">
              <div v-if="!studentDashboardDrives.length" class="col-12">
                <div class="alert alert-info">No eligible drives available at the moment.</div>
              </div>
              <div class="col-md-4" v-for="d in studentDashboardDrives" :key="d.id">
                <div class="card h-100">
                  <div class="card-body d-flex flex-column">
                    <h5 class="card-title">{{ d.job_title }}</h5>
                    <p class="mb-1"><strong>Company:</strong> {{ d.company?.company_name }}</p>
                    <p class="mb-1"><strong>Package:</strong> {{ d.package_lpa }} LPA</p>
                    <p class="mb-1"><strong>Branches:</strong> {{ d.eligible_branches }}</p>
                    <p class="mb-2"><strong>Deadline:</strong> {{ new Date(d.application_deadline).toLocaleString() }}</p>
                    <p class="flex-grow-1 text-muted small">{{ d.job_description }}</p>
                    <div v-if="d.eligibility && d.eligibility.is_eligible === false" class="alert alert-warning py-2 small mb-2">
                      <strong>Not eligible:</strong> {{ d.eligibility.reason }}
                    </div>
                    <div v-else-if="d.deadline_passed" class="alert alert-secondary py-2 small mb-2">
                      <strong>Closed:</strong> Deadline passed.
                    </div>
                    <div v-else-if="d.already_applied" class="alert alert-info py-2 small mb-2">
                      <strong>Applied:</strong> You already applied to this drive.
                    </div>
                    <div class="d-flex gap-2 mt-auto">
                      <button class="btn btn-outline-primary flex-grow-1" @click="loadStudentDriveDetails(d.id)">View details</button>
                      <button class="btn btn-primary flex-grow-1" @click="applyToDrive(d.id)" :disabled="!d.can_apply">
                        Apply
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div v-if="currentPage === 'studentDriveDetails'">
            <div class="d-flex justify-content-between align-items-center mb-3">
              <h4 class="mb-0">Drive Details</h4>
              <button class="btn btn-sm btn-outline-secondary" @click="navigateTo('studentDashboard')">Back</button>
            </div>
            <div v-if="!studentSelectedDrive" class="alert alert-info">Loading drive...</div>
            <div v-else class="card">
              <div class="card-body">
                <div class="d-flex flex-wrap justify-content-between align-items-start gap-2 mb-3">
                  <div>
                    <h5 class="mb-1">{{ studentSelectedDrive.job_title }}</h5>
                    <div class="text-muted">
                      {{ studentSelectedDrive.company?.company_name }} — {{ studentSelectedDrive.package_lpa }} LPA
                    </div>
                  </div>
                  <div class="text-end">
                    <div><strong>Deadline:</strong> {{ new Date(studentSelectedDrive.application_deadline).toLocaleString() }}</div>
                    <div><strong>Eligible branches:</strong> {{ studentSelectedDrive.eligible_branches }}</div>
                    <div><strong>Min CGPA:</strong> {{ studentSelectedDrive.min_cgpa }}</div>
                    <div><strong>Passout year:</strong> {{ studentSelectedDrive.eligible_passout_year }}</div>
                  </div>
                </div>

                <div class="mb-3">
                  <h6 class="mb-2">Job Description</h6>
                  <div class="text-muted" style="white-space: pre-wrap;">{{ studentSelectedDrive.job_description }}</div>
                </div>

                <div v-if="studentSelectedDrive.eligibility && studentSelectedDrive.eligibility.is_eligible === false" class="alert alert-warning">
                  <strong>Not eligible:</strong> {{ studentSelectedDrive.eligibility.reason }}
                </div>
                <div v-else-if="studentSelectedDrive.deadline_passed" class="alert alert-secondary">
                  <strong>Closed:</strong> Deadline passed.
                </div>
                <div v-else-if="studentSelectedDrive.already_applied" class="alert alert-info">
                  <strong>Applied:</strong> You already applied to this drive.
                </div>

                <div class="text-end">
                  <button class="btn btn-primary" @click="applyToDrive(studentSelectedDrive.id)" :disabled="!studentSelectedDrive.can_apply">
                    Apply to this drive
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div v-if="currentPage === 'studentProfile'">
            <h4 class="mb-3">Student Profile</h4>
            <div v-if="studentProfile" class="card">
              <div class="card-body">
                <div class="row g-3">
                  <div class="col-md-6">
                    <label class="form-label">Full Name</label>
                    <input v-model="studentProfile.full_name" type="text" class="form-control" />
                  </div>
                  <div class="col-md-6">
                    <label class="form-label">Roll Number</label>
                    <input v-model="studentProfile.roll_number" type="text" class="form-control" />
                  </div>
                  <div class="col-md-4">
                    <label class="form-label">Branch</label>
                    <input v-model="studentProfile.branch" type="text" class="form-control" />
                  </div>
                  <div class="col-md-4">
                    <label class="form-label">Year of Passout</label>
                    <input v-model="studentProfile.year_of_passout" type="number" min="2000" max="2100" class="form-control" />
                  </div>
                  <div class="col-md-4">
                    <label class="form-label">CGPA</label>
                    <input v-model="studentProfile.cgpa" type="number" step="0.1" class="form-control" />
                  </div>
                  <div class="col-md-6">
                    <label class="form-label">Phone (10 digits)</label>
                    <input v-model="studentProfile.phone" type="text" inputmode="numeric" maxlength="10" class="form-control" placeholder="10-digit mobile number" />
                  </div>
                  <div class="col-md-6">
                    <label class="form-label">Resume</label>
                    <input type="file" class="form-control" @change="uploadResume" />
                    <div v-if="studentProfile.resume_path" class="mt-1">
                      <button class="btn btn-link p-0" @click="viewCurrentResume">View current resume</button>
                    </div>
                  </div>
                </div>
                <div class="mt-3 text-end">
                  <button class="btn btn-primary" @click="submitStudentProfile">Save Profile</button>
                </div>
              </div>
            </div>
            <div v-else class="alert alert-info">Loading profile...</div>
          </div>

          <div v-if="currentPage === 'studentApplications'">
            <div class="d-flex justify-content-between align-items-center mb-3">
              <h4 class="mb-0">Applications</h4>
              <button class="btn btn-sm btn-outline-primary" @click="startExport">Export Applications (CSV)</button>
            </div>
            <table class="table table-hover table-striped table-responsive">
              <thead>
                <tr>
                  <th>Company</th>
                  <th>Job</th>
                  <th>Applied At</th>
                  <th>Status</th>
                  <th>Offer Letter</th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="!studentApplications.length">
                  <td colspan="5" class="text-center text-muted">No applications yet.</td>
                </tr>
                <tr v-for="a in studentApplications" :key="a.id">
                  <td>{{ a.drive?.company?.company_name }}</td>
                  <td>{{ a.drive?.job_title }}</td>
                  <td>{{ new Date(a.applied_at).toLocaleString() }}</td>
                  <td>
                    <span class="badge"
                      :class="{
                        'bg-secondary': a.status === 'applied',
                        'bg-info text-dark': a.status === 'shortlisted',
                        'bg-success': a.status === 'selected',
                        'bg-danger': a.status === 'rejected'
                      }"
                    >
                      {{ a.status }}
                    </span>
                  </td>
                  <td>
                    <button
                      v-if="a.offer_letter_path && (a.status === 'selected')"
                      class="btn btn-sm btn-outline-primary"
                      @click="viewOfferLetter(a.id)"
                    >
                      View
                    </button>
                    <span v-else class="text-muted">N/A</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>
  `
}).mount('#app');

