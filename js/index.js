var page_machados = "machados.html"
var page_enemy_creator = "monsterCreator.html"

function go_to_machado() {
    window.location.replace(page_machados)
}

function go_to_enemy_creator() {
    window.location.replace(page_enemy_creator)
}

const mode = document.getElementById('mode_icon');

mode.addEventListener('click', () => {
    const form = document.getElementById('login_form');
    const body = document.getElementById('body');

    if(mode.classList.contains('fa-moon')) {
        mode.classList.remove('fa-moon');
        mode.classList.add('fa-sun');

        form.classList.add('dark');
        body.classList.add('dark');
        return ;
    }
    
    mode.classList.remove('fa-sun');
    mode.classList.add('fa-moon');

    form.classList.remove('dark');
    body.classList.remove('dark');
});

