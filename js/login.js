api_login = "https://a20wp7bmtb.execute-api.sa-east-1.amazonaws.com/dev";



function loginValidation(user, senha) {
    //console.log("Fetch")
    console.log(senha, user)
    fetch(api_login,
        {
            method: "POST",
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({
                "user": user,
                "senha": senha
            })
        }
    ).then(response => response.json())
        .then(code => {
            if (code.statusCode == 404) { //Se o retorno do fetch for o status code 404, not found ele retorna 0.
                let failedLogin = document.getElementById('failedLogin');
                failedLogin.setAttribute('style', 'display:block; color: red; margin-top: 5%;');
                failedLogin.innerHTML = '"E-mail" ou "Senha" incorretos!';
                return 0;
            }
            //clearMessageErroLogin();
            changeToAdminConsole(code.user);

        })
}


function changeToAdminConsole() {
    window.location.href = "\\lobby.html";
   
}

function clearMessageErroLogin() {
    let failedLogin = document.getElementById('waring_login');
    failedLogin.setAttribute('style', 'display:none; color: red; margin-top: 5%;');
}

function login() {
    let user = document.getElementById('username').value;
    let senha = document.getElementById('password').value;
    //senha = btoa(senha);
    if (validarCamposVazios(user, senha)) {
        loginValidation(user, senha);
    }

}

function validarCamposVazios(email, senha) {
    if (senha == '' | email == '') {
        window.alert('Campos requeridos vazios!');
        return false;
    }
    return true;
}