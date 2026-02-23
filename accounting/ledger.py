

class Ledger:
    def __init__(self):
        self.table=[]

        self.agents=["w", "c", "cf", "kf", "b", "g"]
        self.entries=[]

    def add_entry(self, entry):
        self.entries.append(entry)

    def print_summary(self):
        # Header
        table = f"{'Descs':<15} | {'Workers':<10} | {'Capitalists':<10} | {'c_firms':<10} | {'k_firms':<10}  | {'bank':<10} | {'Government':<10} \n"
        table += "-" * 75 + "\n"

        w=0
        c=0
        cf=0
        kf=0
        b=0
        g=0

        # Rows
        for e in self.entries:
            w+=e.w
            c+=e.c
            cf+=e.cf
            kf+=e.kf
            b+=e.b
            g+=e.g

        table += f"{'Total':<15} | {w:<10} | {c:<10} | {cf:<10} | {kf:<10} | {b:<10} | {g:<10}\n"

        print(table)

    def __str__(self):
        # Header
        table = f"{'Descs':<15} | {'Workers':<10} | {'Capitalists':<10} | {'c_firms':<10} | {'k_firms':<10}  | {'bank':<10} | {'Government':<10} \n"
        table += "-" * 75 + "\n"

        # Rows
        for e in self.entries:
            table += f"{e.descr:<15} | {e.w:<10} | {e.c:<10} | {e.cf:<10} | {e.kf:<10} | {e.b:<10} | {e.g:<10}\n"

        return table

class Entry:
    def __init__(self, descr, amount, frm, to):
        self.descr = descr
        self.w=0
        self.c=0
        self.cf=0
        self.kf=0
        self.b=0
        self.g=0
        self.konteeri(amount, frm, to)

    def konteeri(self, amount, frm, to):

        match frm:
            case "w":
                self.w=-amount
            case "c":
                self.c=-amount
            case "cf":
                self.cf=-amount
            case "kf":
                self.kf=-amount
            case "b":
                self.b=-amount
            case "g":
                self.g=-amount
            case _:
                pass

        match to:
            case "w":
                self.w=amount
            case "c":
                self.c=amount
            case "cf":
                self.cf=amount
            case "kf":
                self.kf=amount
            case "b":
                self.b=amount
            case "g":
                self.g=amount
            case _:
                pass


if __name__=="__main__":
    pass
    """ Testing
    l=Ledger()
    l.add_entry(Entry("wage", 10, "cf", "w"))
    l.add_entry(Entry("div", 10, "cf", "c"))

    print(l)
    l.print_summary()
    """