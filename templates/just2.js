<script>
const editBtn = document.getElementById('editBtn');
const saveBtn = document.getElementById('saveBtn');
const form = document.getElementById('profileForm');

editBtn.addEventListener('click', () => {
    form.querySelectorAll('input').forEach(input => input.removeAttribute('readonly'));
    editBtn.style.display = 'none';
    saveBtn.style.display = 'inline-block';
});

saveBtn.addEventListener('click', () => {
    const data = {};
    form.querySelectorAll('input').forEach(input => data[input.name] = input.value);

    fetch('/update_profile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(data)
    })
    .then(res => res.json())
    .then(res => {
        if(res.success) {
            alert(res.message);
            // Update inputs with latest data
            for(let key in res.user){
                form.querySelector(`input[name=${key}]`).value = res.user[key];
                form.querySelector(`input[name=${key}]`).setAttribute('readonly', true);
            }
            editBtn.style.display = 'inline-block';
            saveBtn.style.display = 'none';
        }
    });
});
</script>
