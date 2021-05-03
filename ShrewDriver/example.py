class Contact:

    def __init__(self):
        self.name = ""
        self.phone_number = 0
        self.email = ""
        self.contact = {}

    def add_name(self):
        self.name = raw_input("Add name: ")

    def add_email(self):
        self.email = raw_input('Add email: ')

    def add_phone(self):
        self.phone_number = raw_input('Add phone number: ')

    def contact(self):
        self.contact['name'] = self.name
        self.contact['number'] = self.phone_number
        self.contact['email'] = self.email
        return self.contact


if __name__ == '__main__':
    Frank = Contact()
    Matt = Contact()
    print 'hi'
    