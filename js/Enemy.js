export class Enemy {

    constructor(name, baseVida, nivel, tier, forca, destreza, constituicao, inteligencia, sabedoria, carisma, arma, armadura, aleatorio) {
        this.name = name;
        this.baseVida = baseVida;
        this.nivel = nivel;
        this.tier = tier;
        this.proficiencia = Math.floor(this.nivel / 2) + 1;
        this.forca = forca;
        this.destreza = destreza;
        this.constituicao = constituicao;
        this.inteligencia = inteligencia;
        this.sabedoria = sabedoria;
        this.carisma = carisma;
        if (aleatorio == true) {
            this.randomAtributes();
        }
        this.difficult = this.updateAtributes(tier);
        this.arma = this.myWeapon(arma);
        this.mods = this.setModificadores();
        this.vidaMaxima = Math.ceil(this.updateVidaMaxima());
        this.manaMaxima = Math.ceil(this.gerarMana());
        this.armadura = armadura;
        this.Ca = this.gerarCA();
        this.dano = this.generalAttack()[1];
        this.ataque = this.generalAttack()[0];
        this.skills = [];

    }

    updateVidaMaxima() {
        let vida = (this.baseVida + (this.gerarModificador(this.constituicao) * this.nivel)) * this.getTierLifeBonus() + this.generateDice(8);
        return vida;
    }

    generateDice(dado) {
        let dice = 0;
        for (let i = 0; i <= this.nivel - 1; i++) {
            dice += Math.random() * dado + 1;
        }

        return dice;
    }

    generateDiceValue() {
        let atribute = Math.floor(Math.random() * 9 + 10);
        return atribute;

    }

    getTierLifeBonus() {
        if (this.tier == "Normal") {
            return 1;
        } else if (this.tier == "Elite") {
            return 8;
        } else if (this.tier == "Boss") {
            return 16;
        }
    }

    gerarModificador(atributo) {
        let modificador = atributo / 2 - 5;
        return Math.floor(modificador);
    }

    getModificadores() {
        return this.mods;
    }

    gerarMana() {
        let dadoBase = Math.random() * 6 + 1
        let mana = (this.gerarModificador(this.inteligencia) + 1) * this.nivel + dadoBase + 6;
        if (this.tier == 'Elite') {
            mana *= 2;
        } else if (this.tier == 'Boss') {
            mana *= 4;
        }
        return mana;
    }

    gerarCA() {
        let armadura = this.armadura + this.gerarModificador(this.destreza) + 10;
        if (this.tier == 'Elite') {
            armadura += 5;
        } else if (this.tier == 'Boss') {
            armadura += 10;
        }
        return Math.floor(armadura);
    }

    setModificadores() {
        let modificadores = [];
        modificadores.push(this.gerarModificador(this.forca));
        modificadores.push(this.gerarModificador(this.destreza));
        modificadores.push(this.gerarModificador(this.constituicao));
        modificadores.push(this.gerarModificador(this.inteligencia));
        modificadores.push(this.gerarModificador(this.sabedoria));
        modificadores.push(this.gerarModificador(this.carisma));

        return modificadores;
    }

    myWeapon(arma) {
        if (arma == 0) {
            this.arma = this.randomWeapon();
        } else {
            this.arma = arma;
        }
        return arma;
    }

    randomWeapon() {
        let armas = ["Adaga", "Arco", "Besta", "Firegun", "Espada", "Espadão", "Machado", "Machadão", "Foice", "Orbe", "Cajado", "Dual", "Lança", "Swallow", "Haloblade", "Katana", "Estilingue", "Soqueira", "Martelo", "Sem Arma"];
        let value = Math.random(armas.length - 1);
        let arma = armas[value];
        return arma;
    }

    generateEnemy() {
        let monster =
        {
            "nome": this.name,
            "nivel": this.nivel,
            "tier": this.tier,
            "proficiencia": this.proficiencia,
            "vida": this.vidaMaxima,
            "mana": this.manaMaxima,
            "forca": this.forca,
            "destreza": this.destreza,
            "constituicao": this.constituicao,
            "inteligencia": this.inteligencia,
            "sabedoria": this.sabedoria,
            "carisma": this.carisma,
            "modificadores": this.mods,
            "arma": this.arma,
            "ataque": this.ataque,
            "ca": this.ca,
            "dano": {},
            "habilidades": []
        }

        return monster;
    }

    generalAttack() {
        let weaponType = this.weaponAttackAndDMG();
        let tier = this.tier;
        let result = String(Math.floor(this.nivel / 4)) + weaponType;
        if (tier == 'Elite') {
            weaponType[1] = String(Math.floor(this.nivel / 4)) + weaponType[1];
            weaponType[0] = weaponType[0] + "+5";
            result = weaponType;
        } else if (tier == 'Boss') {
            weaponType[1] = "4x(" + String(Math.floor(this.nivel / 4)) + weaponType[1] + ")";
            weaponType[0] = weaponType[0] + "+15";
            result = weaponType;
        } else if (tier == 'Normal') {
            weaponType[1] = String(Math.floor(this.nivel / 4)) + weaponType[1];
            result = weaponType;
        }
        return result;
    }

    allWeapons() {
        let armas = ["Adaga", "Arco", "Besta", "Firegun", "Espada", "Espadão", "Machado", "Machadão", "Foice", "Orbe", "Cajado", "Dual", "Lança", "Swallow", "Haloblade", "Katana", "Estilingue", "Soqueira", "Martelo", "Sem Arma"]
        return armas;
    }


    weaponAttackAndDMG() {
        let armas = this.allWeapons();
        let myWeapon = String(this.arma);
        let arma = '';
        let attack = '';
        if (myWeapon == armas[0]) {
            arma = "d6+" + String(this.mods[1]) + "+" + String(this.proficiencia);
            attack = "D20+" + String(this.mods[1]) + "+" + String(this.proficiencia);
        } else if (myWeapon == armas[1]) {
            arma = "d10+" + String(this.mods[1]) + "+" + String(this.proficiencia);
            attack = "D20+" + String(this.mods[1]) + "+" + String(this.proficiencia);
        } else if (myWeapon == armas[2]) {
            arma = "d12+" + String(this.mods[0]) + "+" + String(this.proficiencia);
            attack = "D20+" + String(this.mods[0]) + "+" + String(this.proficiencia);
        } else if (myWeapon == armas[3]) {
            arma = "d10+" + String(this.mods[1]) + "+" + String(this.proficiencia);
            attack = "D20+" + String(this.mods[1]) + "+" + String(this.proficiencia);
        } else if (myWeapon == armas[4]) {
            arma = "d8+" + String(this.mods[1]) + "+" + String(this.proficiencia);
            attack = "D20+" + String(this.mods[1]) + "+" + String(this.proficiencia);
        } else if (myWeapon == armas[5]) {
            arma = "d12+" + String(this.mods[0]) + "+" + String(this.proficiencia);
            attack = "D20+" + String(this.mods[0]) + "+" + String(this.proficiencia);
        } else if (myWeapon == armas[6]) {
            arma = "d8+" + String(this.mods[1]) + "+" + String(this.proficiencia);
            attack = "D20+" + String(this.mods[1]) + "+" + String(this.proficiencia);
        } else if (myWeapon == armas[7]) {
            arma = "d12+" + String(this.mods[0]) + "+" + String(this.proficiencia);
            attack = "D20+" + String(this.mods[0]) + "+" + String(this.proficiencia);
        } else if (myWeapon == armas[8]) {
            arma = "d12+" + String(this.mods[1]) + "+" + String(this.proficiencia);
            attack = "D20+" + String(this.mods[1]) + "+" + String(this.proficiencia);
        } else if (myWeapon == armas[9]) {
            arma = "d10+" + String(this.mods[3]) + "+" + String(this.proficiencia);
            attack = "D20+" + String(this.mods[3]) + "+" + String(this.proficiencia);
        } else if (myWeapon == armas[10]) {
            arma = "d10+" + String(this.mods[3]) + "+" + String(this.proficiencia);
            attack = "D20+" + String(this.mods[3]) + "+" + String(this.proficiencia);
        } else if (myWeapon == armas[11]) {
            arma = "d16+" + String(this.mods[1]) + "+" + String(this.proficiencia);
            attack = "D20+" + String(this.mods[1]) + "+" + String(this.proficiencia);
        } else if (myWeapon == armas[12]) {
            arma = "d12+" + String(this.mods[0]) + "+" + String(this.proficiencia);
            attack = "D20+" + String(this.mods[0]) + "+" + String(this.proficiencia);
        } else if (myWeapon == armas[13]) {
            arma = "d14+" + String(this.mods[0]) + "+" + String(this.proficiencia);
            attack = "D20+" + String(this.mods[0]) + "+" + String(this.proficiencia);
        } else if (myWeapon == armas[14]) {
            arma = "d10+" + String(this.mods[1]) + "+" + String(this.proficiencia);
            attack = "D20+" + String(this.mods[1]) + "+" + String(this.proficiencia);
        } else if (myWeapon == armas[15]) {
            arma = "d10+" + String(this.mods[0]) + "+" + String(this.proficiencia);
            attack = "D20+" + String(this.mods[0]) + "+" + String(this.proficiencia);
        } else if (myWeapon == armas[16]) {
            arma = "d7+" + String(this.mods[1]) + "+" + String(this.proficiencia);
            attack = "D20+" + String(this.mods[1]) + "+" + String(this.proficiencia);
        } else if (myWeapon == armas[17]) {
            arma = "d8+" + String(this.mods[0]) + "+" + String(this.proficiencia);
            attack = "D20+" + String(this.mods[0]) + "+" + String(this.proficiencia);
        } else if (myWeapon == armas[18]) {
            arma = "d12+" + String(this.mods[0]) + "+" + String(this.proficiencia);
            attack = "D20+" + String(this.mods[0]) + "+" + String(this.proficiencia);
        } else if (myWeapon == armas[19]) {
            arma = "d4+" + String(this.mods[0]) + "+" + String(this.mods[1]) + "+" + String(this.proficiencia);
            attack = "D20+" + String(this.mods[0]) + "+" + String(this.mods[1]) + "+" + String(this.proficiencia);
        }

        let result = [attack, arma];
        return result;
    }

    updateAtributes(tier) {
        let elite = Math.floor(this.nivel / 2);
        let boss = this.nivel;
        if (tier == 'Elite') {
            this.forca += elite;
            this.destreza += elite;
            this.constituicao += elite;
            this.inteligencia += elite;
            this.sabedoria += elite;
            this.carisma += elite;
            return 'Hard';
        } else if (tier == 'Boss') {
            this.forca += boss;
            this.destreza += boss;
            this.constituicao += boss;
            this.inteligencia += boss;
            this.sabedoria += boss;
            this.carisma += boss;
            return 'Nightmare';
        }
        return 'Normal';
    }

    randomAtributes() {
        this.forca = this.generateDiceValue();
        this.destreza = this.generateDiceValue();
        this.constituicao = this.generateDiceValue();
        this.inteligencia = this.generateDiceValue();
        this.sabedoria = this.generateDiceValue();
        this.carisma = this.generateDiceValue();
    }


}