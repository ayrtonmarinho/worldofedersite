
class Personagem {
    constructor(nome, nivel, dadoVida, armadura, forca, destreza, constituicao, inteligencia, sabedoria, carisma) {
        this.nome = nome;
        this.escolas = [];
        this.escolasMundo = [];
        this.treinamentos = [];
        this.forca = forca;
        this.destreza = destreza;
        this.constituicao = constituicao;
        this.inteligencia = inteligencia;
        this.sabedoria = sabedoria;
        this.carisma = carisma;
        this.vidaMaxima = 1;
        this.dadoVida = dadoVida;
        this.manaMaxima = 1;
        this.Ca = this.gerarCA;
        this.armadura = 0;



    };

    gerarModificador(atributo) {
        valor = atributo / 2 - 5;
        return valor;
    }

    gerarVidaMaxima() {
        vida = this.vidaMaxima + (this.nivel * this.gerarModificador(this.constituicao)) + this.dadoVida;
        return vida;
    }

    updateVida(dadoVida, vetorBonus) {
        // vetorBonus é defindo por [bonus1, bonus2, bonus3, ...]
        vidaAtual = this.vidaMaxima;
        for (let i = 0; i < vetorBonus.length; i++) {
            console.log(i)
        }
    }

    gerarCA() {
        classeArmadura = this.gerarModificador(this.destreza) + this.armadura + 10;
        return classeArmadura;
    }


}

