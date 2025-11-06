// TemplateService.cs
using System.Collections.Generic;

public class TemplateService
{
    private readonly Dictionary<int, string> _map = new()
    {
        [0] = "Havarija - poziv rukovodiocu",
        [1] = "Zivotinje",
        [2] = "Ptice",
        [3] = "Insekti",
        [4] = "Predmeti",
        [5] = "Zelenilo",
        [6] = "Alarm van cuvanog objekta",
        [7] = "Padavine",
        [8] = "Sum u slici",
        [9] = "Mutna slika / tamper",

        [10] = "Periodicni pregled stanja na objektu",
        [11] = "Nedozvoljena ili sumnjiva aktivnost",
        [12] = "Nedozvoljen ili sumnjiv ulazak/boravak",
        [13] = "Zaposleni na pogresnom ili zabranjenom mestu",
        [14] = "MTS na nedozvoljenom mestu",
        [15] = "Previse ljudi na sticenom prostoru",

        [16] = "Nepoznato lice u prolazu",
        [17] = "Nepoznato lice se zadrzava i vrsi sumnjiv rad",
        [18] = "Nepoznato lice - razglas poslat, lice napusta objekat",
        [19] = "Nepoznato lice - razglas poslat, lice ne napusta objekat - poslata patrola",

        [20] = "Gost van planirane putanje",
        [21] = "Gost van planiranog vremena",

        [22] = "Zaposleni dolazi na posao",
        [23] = "Zaposleni odlazi sa posla",
        [24] = "Zaposleni se zadrzava posle radnog vremena",
        [25] = "Zaposleni u firmi van radnog vremena",
        [26] = "Zaposleni van predvidjene putanje",
        [27] = "Zaposleni - redovan rad",

        [28] = "Sluzbeno vozilo u prolazu u radno vreme",
        [29] = "Sluzbeno vozilo/radna masina van plana",
        [30] = "Sluzbeno vozilo/radna masina na pogresnom mestu",
        [31] = "Sluzbeno vozilo/radna masina van putanje",
        [32] = "Sluzbeno vozilo/radna masina - redovan rad",

        [33] = "DKP vozilo van putanje",
        [34] = "DKP vozilo van mesta",
        [35] = "DKP vozilo van vremena",
        [36] = "DKP vozilo - planiran rad",

        [37] = "Privatno vozilo u prolazu (radno)",
        [38] = "Privatno vozilo u prolazu (van radnog)",
        [39] = "Privatno vozilo se zadrzava u krugu"
    };

    public string GetName(int id) =>
        _map.TryGetValue(id, out var name) ? name : "Nepoznat sablon";
}
