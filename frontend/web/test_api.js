import axios from 'axios';

const test = async () => {
    try {
        // Authenticate first
        const authRes = await axios.post('http://127.0.0.1:8000/api/accounts/login/', {
            username: 'admin',
            password: 'admin'
        });
        const token = authRes.data.access;
        const headers = { Authorization: `Bearer ${token}` };

        // Create Case
        const caseData = {
            case_number: `AI-FOR-${Math.floor(Math.random() * 1000000)}`,
            title: `Forensic Examination: General UDisk`,
            description: `Test`,
            priority: 'high',
            case_type: 'Digital Forensics'
        };
        let caseRes;
        try {
            caseRes = await axios.post('http://127.0.0.1:8000/api/cases/', caseData, { headers });
            console.log("Case created:", caseRes.data._id);
        } catch (e) {
            console.error("Case Error:", e.response ? e.response.data.substring(0, 500) : e.message);
            return;
        }

        const evidenceData = {
            case_id: caseRes.data._id,
            evidence_type: 'disk_image',
            file_name: `General UDisk_Forensic_Image`,
            file_path: `D:\\`,
            file_size: 31460590387,
            description: `Test`,
            status: 'collected'
        };
        try {
            const evRes = await axios.post('http://127.0.0.1:8000/api/evidence/', evidenceData, { headers });
            console.log("Evidence created:", evRes.data._id);
        } catch (e) {
            console.error("Evidence Error:", e.response ? e.response.data.substring(0, 500) : e.message);
        }
        
    } catch (e) {
        console.error("Error:", e.response ? e.response.data : e.message);
    }
}
test();
