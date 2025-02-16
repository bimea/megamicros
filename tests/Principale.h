// line 255: INIT FX3
// Line 1231: reset ALTERA

#pragma once
// version mai 2019
#pragma warning( disable : 4200 )
#pragma warning( disable : 4244 )
#pragma warning( disable : 4099 )

#define _ADDR_LECT			0x81	//lecture   
#define _ADDR_ECR			0x01	//�criture
#define	VENDOR_ID			0x0483
#define	PRODUCT_ID			0x5740  // Carte sondeur g�n�r� par Cube
#define TIMEOUT				4000  //ms  pour les op�rations standard
#define INTERFAC			1 //choix de l'interface
#define N_FILTRE			48
#define NORM_FILTRE			13421726
#define C_RESET_ALTERA		0xB0
#define C_INIT_SIGMA		0xB1
#define C_FILTRE			0xB2
#define C_PLL				0xB3
#define C_EMISSION			0xB4
#define C_RECEP				0xB5
#define C_EM_REC			0xB6
#define RF					4		// Fhetero/Fech
#define LONG_LIGNE			0xC000  // nb maximal d'�chantillons h�t�rodyn�s
#define COEFF_IMAGE			2		//facteur multiplicatif pour l'�chelle de gris

static int NT_VAL[5] = {16,8,4,2,1}; 

#include "math.h"
#include < stdio.h >
#include < vcclr.h >
#include "libusb.h"
#include <cmath>

namespace SLBP
{
	using namespace System;
	using namespace System::ComponentModel;
	using namespace System::Collections;
	using namespace System::Windows::Forms;
	using namespace System::Data;
	using namespace System::Drawing;
    using namespace System::Threading;
	using namespace System::IO::Ports;
	using namespace System::IO;
	using namespace System::Runtime::InteropServices;


	public ref class Principale : public System::Windows::Forms::Form
	{
	public:
		Principale(void)
		{
			InitializeComponent();
			TimeOut = TIMEOUT;
			buflen = new LONG;
			buf = new unsigned char[256];
			txtBox_Info = textBox_Info;
			libusb_init(NULL);
			libusb_set_debug(NULL, 3);
			f_ech = 400;
			NT = 8;
			listBox_NT->TopIndex = 2;
			listBox_NT->Refresh();
			PLL_Init = false;
			Emis_Init = false;
			Rec_Init = false;
			Fich_open = false;
			dessin = 10;
			W_image = pictureBox_Image->Width;
			H_image = pictureBox_Image->Height;
			vScrollBar_Image->Maximum = H_image + vScrollBar_Image->LargeChange - 1;
			vScrollBar_Image->Minimum = 0;
			MaximumSize = Size;
			MinimumSize = Size;
			num_ligne = 0;
			Color couleur = ColorTranslator::FromOle(0);
			Drawing::Rectangle rect = Drawing::Rectangle(0, 0, W_image, H_image * 2);
			Image_bitmap = gcnew Bitmap(W_image, H_image * 2);
			for (int i = 0;i < H_image * 2; i++) for (int j = 0; j < W_image; j++) Image_bitmap->SetPixel(j, i, couleur);
			pictureBox_Image->Image = Image_bitmap;
			pictureBox_Image->Refresh();
			vScrollBar_Image->Enabled = true;
			derniere_ligne = false;
			data = (char *) calloc(2 * H_image*LONG_LIGNE, 1);
			data_image = (char *)calloc(W_image*H_image * 2 * 4, 1);
			init_fait = false;
			init_USB = false;
			num = 0;
		}

	protected:
		~Principale()
		{
			if (handle)
			{
				libusb_release_interface(handle, INTERFAC);
				libusb_close(handle);
			}
			libusb_exit(NULL);
			if (components)	delete components;
		}

	public:
		LONG *buflen;
		static System::Windows::Forms::TextBox^  txtBox_Info;
		static libusb_device_handle *handle, *hand;
		static libusb_transfer_cb_fn callback;
		static libusb_transfer *transfert;
		static unsigned char *buffers;
		static bool transfert_fini,ligne_a_afficher,init_fait, init_USB,test;
		static int retour, TimeOut = 10000, NT;
		static unsigned char *buf;
		static char *data,*data_image;
		static FILE *Fich, *Fich_test, *Fich_log;
		static float f_ech, duree_emis, duree_tps_mort, bande;
		static unsigned long nb_echant, num_tir, nb_tirs,num_ligne;
		static bool PLL_Init, Emis_Init, Rec_Init, Fich_open, Stop, derniere_ligne;
		int dessin, W_image, H_image, premiere_ligne,num;
		Bitmap^ Image_bitmap;

	private: System::Windows::Forms::Button^  button_Init;
	private: System::Windows::Forms::TextBox^  textBox_Info;
	private: System::ComponentModel::Container ^components;
	private: System::Windows::Forms::Button^  button_InitSigma;
	private: System::Windows::Forms::Button^  button_Recep;
	private: System::Windows::Forms::Button^  button_Filtre;

	private: System::Windows::Forms::NumericUpDown^  numericUpDown_Echantillons;
	private: System::Windows::Forms::Label^  label_Duree;
	private: System::Windows::Forms::Label^  label_Echantillons;
	private: System::Windows::Forms::Button^  button_Emission;
	private: System::Windows::Forms::NumericUpDown^  numericUpDown_PLL;
	private: System::Windows::Forms::Label^  label_PLL;
	private: System::Windows::Forms::ListBox^  listBox_NT;
	private: System::Windows::Forms::Label^  label_NT;
	private: System::Windows::Forms::Button^  button_Start;
	private: System::Windows::Forms::GroupBox^  groupBox_Test;
	private: System::Windows::Forms::GroupBox^  groupBox_Recep;
	private: System::Windows::Forms::GroupBox^  groupBox_Emis;
	private: System::Windows::Forms::GroupBox^  groupBox_Heter;
	private: System::Windows::Forms::GroupBox^  groupBox_Duree;
	private: System::Windows::Forms::NumericUpDown^  numericUpDown_Emis;
	private: System::Windows::Forms::Label^  label_D_Emis;
	private: System::Windows::Forms::Label^  label_Emis;
	private: System::Windows::Forms::GroupBox^  groupBox_Bande;
	private: System::Windows::Forms::NumericUpDown^  numericUpDown_Bande;
	private: System::Windows::Forms::Label^  label_Bande;
	private: System::Windows::Forms::GroupBox^  groupBox_Tps_mort;
	private: System::Windows::Forms::NumericUpDown^  numericUpDown_Tps_mort;
	private: System::Windows::Forms::Label^  label_Tps_mort;
	private: System::Windows::Forms::Label^  label3;
	private: System::Windows::Forms::Button^  button_Initialisation;
	private: System::Windows::Forms::GroupBox^  groupBox_EmRec;
	private: System::Windows::Forms::Button^  button_Fichier;
	private: System::Windows::Forms::GroupBox^  groupBox_Periode;
	private: System::Windows::Forms::NumericUpDown^  numericUpDown_Periode;
	private: System::Windows::Forms::Label^  label_Periode;
	private: System::Windows::Forms::GroupBox^  groupBox_Nb_Tirs;
	private: System::Windows::Forms::NumericUpDown^  numericUpDown_Nb_Tirs;
	private: System::Windows::Forms::Label^  label_Nb_Tirs;
	private: System::Windows::Forms::Button^  button_Stop;
	private: System::Windows::Forms::SaveFileDialog^  saveFileDialog_Data;
	private: System::Windows::Forms::PictureBox^  pictureBox_Image;
	private: System::Windows::Forms::Button^  button_Image;
	private: System::Windows::Forms::VScrollBar^  vScrollBar_Image;
	private: System::Windows::Forms::GroupBox^  groupBox_Image;
	private: System::Windows::Forms::Button^  button_Eff_Image;
	private: System::Windows::Forms::CheckBox^  checkBox_Test;
	private: System::Windows::Forms::GroupBox^  groupBox_PLL;
	private: System::Windows::Forms::GroupBox^  groupBox_Config;
	private: System::Windows::Forms::GroupBox^  groupBox_Echantillons;
	private: System::Windows::Forms::Button^  button_Config;
	private: System::Windows::Forms::Button^  button_Reset_Altera;

	public:
		static int write_command(libusb_device_handle *udh, int cmd, unsigned char *data, int length)
		{
			int typerequest = LIBUSB_RECIPIENT_DEVICE | LIBUSB_REQUEST_TYPE_VENDOR | LIBUSB_ENDPOINT_OUT;
			int value = 0, index, r;
			int request = cmd;
			index = 0;
			if (!init_USB)
			{
				call_verb("Pas de liaison USB !\n", 1);
				return -1;
			}
			r = libusb_control_transfer(udh, typerequest, request, value, index, data, length, TimeOut);
			return r;
		}
		static int read_command(libusb_device_handle *udh, int request, unsigned char *data, int length)
		{
			int typerequest = LIBUSB_RECIPIENT_DEVICE | LIBUSB_REQUEST_TYPE_VENDOR | LIBUSB_ENDPOINT_IN;
			int value = 0, index = 0;
			return libusb_control_transfer(udh, typerequest, request, value, index, data, length, TimeOut);
		}
		static void __clrcall fn_callback()
		{
			// pr�vu pour que les t�ches de fond ne s'ex�cute qu'une seule fois (pas de relance dan le callback)
			unsigned long rlen;
			int i;
			long int *p;
			float a, b;

			rlen = transfert->actual_length;
			if (transfert->status != LIBUSB_TRANSFER_COMPLETED) //erreur dans le transfert
			{
				if (transfert->status == LIBUSB_TRANSFER_TIMED_OUT)
					call_verb("TIMEOUT lors du transfert \n", 0);
				else
					call_verb(String::Format("Erreur lors du transfert status {0:G}\n", (long)transfert->status), 0);
				libusb_cancel_transfer(transfert);
				transfert_fini = true;
				return;
			}
			else	//transfert OK
			{
				if (!Rec_Init)
				{
					if (test) fwrite(buffers, 1, rlen, Fich_test);

				}
				else fwrite(buffers, 1, rlen, Fich);
			// calcul de l'amplitude brute
				p = (long int *)buffers;
				for (i = 0; i < rlen / 8; i++)
				{
					a = (float) *p++;
					b = (float) *p++;
					*(data +num_ligne*LONG_LIGNE+i) = COEFF_IMAGE * floor(10 * log10(a*a + b * b)); //en dB
				}
				ligne_a_afficher = true;
			}
			transfert_fini = true;
		}
		static void call_verb(String ^verbose, int flag)
		{
			// Transmission de commentaires sous forme de cha�ne de caract�res
			//   0 : INFO : liste courante
			//   1 : ERREUR (bo�te d'alerte) + INFO
			CheckForIllegalCrossThreadCalls = false;
			switch (flag)
			{
			case 0: 	txtBox_Info->AppendText(verbose);
				break; // info
			case 1:  	txtBox_Info->AppendText(verbose);
				MessageBox::Show("Alerte : " + verbose, "Erreur", MessageBoxButtons::OK, MessageBoxIcon::Warning);
				break; // info + alert box
			default: 	txtBox_Info->AppendText(verbose);
				break; // info
			}
		}
		void init_FX3()
		{ //	Initialisation de la liaison USB
			if (handle)
			{
				libusb_release_interface(handle, INTERFAC);
				libusb_close(handle);
			}
			init_USB = false;
			// On retrouve la carte ST par rapport � vendor_id et product_id
			handle = libusb_open_device_with_vid_pid(NULL, VENDOR_ID, PRODUCT_ID); /// VID PID
			if (handle != NULL)
			{
				libusb_claim_interface(handle, INTERFAC);
				if (test) call_verb("D�tection de SLBP OK ! \n", 0);
				init_USB = true;
			}
			else call_verb("Pas de liaison USB !\n", 1);
		}
		void affiche_ligne()
		{
			Bitmap^ bitmap1;
			Imaging::PixelFormat format = pictureBox_Image->Image->PixelFormat;
			Drawing::Rectangle rect = Drawing::Rectangle(0, 0, W_image, H_image * 2);
			Imaging::BitmapData^ bmpData;
			IntPtr ptr;
			array<Byte> ^ligne;
			long int j;

			
			if (derniere_ligne)
			{
				memmove(data_image, (data_image +  W_image * 4), (2*H_image-1) * W_image * 4);
				if(checkBox_Test->Checked) 
					call_verb("Derni�re ligne affich�e \n", 0);
			}
			else
			{
				if (checkBox_Test->Checked) 
					call_verb(String::Format("Ligne affich�e n�{0:G}\n", num_ligne), 0);
			}
			for (j = 0; j < W_image; j++)
			{
				*(data_image + num_ligne * W_image * 4 + 4 * j) = *(data + num_ligne * LONG_LIGNE + j);
				*(data_image + num_ligne * W_image * 4 + 4 * j+1) = *(data + num_ligne * LONG_LIGNE + j);
				*(data_image + num_ligne * W_image * 4 + 4 * j+2) = *(data + num_ligne * LONG_LIGNE + j);
				*(data_image + num_ligne * W_image * 4 + 4 * j+3) = 255;
			}
			bitmap1 = Image_bitmap;
			bmpData = bitmap1->LockBits(rect, Imaging::ImageLockMode::ReadWrite, format);
			ptr = bmpData->Scan0;
			char *p = (char *)bmpData->Scan0.ToPointer();
			memmove(p,(data_image+ premiere_ligne * W_image * 4), H_image * W_image * 4);
			bitmap1->UnlockBits(bmpData);
			pictureBox_Image->Image = bitmap1;
			pictureBox_Image->Refresh();
			ligne_a_afficher = false;
			if (!derniere_ligne) num_ligne++;
			if (num_ligne == 2 * H_image)
			{
				num_ligne--;
				derniere_ligne = true;
			}
		}
		void Enable(bool flag)
		{
			button_Initialisation->Enabled = flag;
			button_Config->Enabled = flag;
			groupBox_Config->Enabled = flag;
			groupBox_Test->Enabled = flag;
			button_Eff_Image->Enabled = flag;
			button_Fichier->Enabled = flag;
			button_Start->Enabled = flag;
			groupBox_Nb_Tirs->Enabled = flag;
			groupBox_Periode->Enabled = flag;
			checkBox_Test->Enabled = flag;
		}

#pragma region Windows Form Designer generated code
		/// <summary>
		/// Required method for Designer support - do not modify
		/// the contents of this method with the code editor.
		/// </summary>
		void InitializeComponent(void)
		{
			this->button_Init = (gcnew System::Windows::Forms::Button());
			this->textBox_Info = (gcnew System::Windows::Forms::TextBox());
			this->button_InitSigma = (gcnew System::Windows::Forms::Button());
			this->button_Recep = (gcnew System::Windows::Forms::Button());
			this->button_Filtre = (gcnew System::Windows::Forms::Button());
			this->button_Reset_Altera = (gcnew System::Windows::Forms::Button());
			this->numericUpDown_Echantillons = (gcnew System::Windows::Forms::NumericUpDown());
			this->label_Echantillons = (gcnew System::Windows::Forms::Label());
			this->label_Duree = (gcnew System::Windows::Forms::Label());
			this->button_Emission = (gcnew System::Windows::Forms::Button());
			this->numericUpDown_PLL = (gcnew System::Windows::Forms::NumericUpDown());
			this->label_PLL = (gcnew System::Windows::Forms::Label());
			this->listBox_NT = (gcnew System::Windows::Forms::ListBox());
			this->label_NT = (gcnew System::Windows::Forms::Label());
			this->button_Start = (gcnew System::Windows::Forms::Button());
			this->groupBox_Test = (gcnew System::Windows::Forms::GroupBox());
			this->button_Initialisation = (gcnew System::Windows::Forms::Button());
			this->button_Image = (gcnew System::Windows::Forms::Button());
			this->checkBox_Test = (gcnew System::Windows::Forms::CheckBox());
			this->groupBox_Recep = (gcnew System::Windows::Forms::GroupBox());
			this->groupBox_Echantillons = (gcnew System::Windows::Forms::GroupBox());
			this->groupBox_Heter = (gcnew System::Windows::Forms::GroupBox());
			this->groupBox_Emis = (gcnew System::Windows::Forms::GroupBox());
			this->groupBox_PLL = (gcnew System::Windows::Forms::GroupBox());
			this->groupBox_Tps_mort = (gcnew System::Windows::Forms::GroupBox());
			this->numericUpDown_Tps_mort = (gcnew System::Windows::Forms::NumericUpDown());
			this->label_Tps_mort = (gcnew System::Windows::Forms::Label());
			this->label3 = (gcnew System::Windows::Forms::Label());
			this->groupBox_Bande = (gcnew System::Windows::Forms::GroupBox());
			this->numericUpDown_Bande = (gcnew System::Windows::Forms::NumericUpDown());
			this->label_Bande = (gcnew System::Windows::Forms::Label());
			this->groupBox_Duree = (gcnew System::Windows::Forms::GroupBox());
			this->numericUpDown_Emis = (gcnew System::Windows::Forms::NumericUpDown());
			this->label_Emis = (gcnew System::Windows::Forms::Label());
			this->label_D_Emis = (gcnew System::Windows::Forms::Label());
			this->groupBox_EmRec = (gcnew System::Windows::Forms::GroupBox());
			this->button_Fichier = (gcnew System::Windows::Forms::Button());
			this->groupBox_Periode = (gcnew System::Windows::Forms::GroupBox());
			this->numericUpDown_Periode = (gcnew System::Windows::Forms::NumericUpDown());
			this->label_Periode = (gcnew System::Windows::Forms::Label());
			this->groupBox_Nb_Tirs = (gcnew System::Windows::Forms::GroupBox());
			this->numericUpDown_Nb_Tirs = (gcnew System::Windows::Forms::NumericUpDown());
			this->label_Nb_Tirs = (gcnew System::Windows::Forms::Label());
			this->button_Eff_Image = (gcnew System::Windows::Forms::Button());
			this->button_Stop = (gcnew System::Windows::Forms::Button());
			this->saveFileDialog_Data = (gcnew System::Windows::Forms::SaveFileDialog());
			this->pictureBox_Image = (gcnew System::Windows::Forms::PictureBox());
			this->vScrollBar_Image = (gcnew System::Windows::Forms::VScrollBar());
			this->groupBox_Image = (gcnew System::Windows::Forms::GroupBox());
			this->groupBox_Config = (gcnew System::Windows::Forms::GroupBox());
			this->button_Config = (gcnew System::Windows::Forms::Button());
			(cli::safe_cast<System::ComponentModel::ISupportInitialize^>(this->numericUpDown_Echantillons))->BeginInit();
			(cli::safe_cast<System::ComponentModel::ISupportInitialize^>(this->numericUpDown_PLL))->BeginInit();
			this->groupBox_Test->SuspendLayout();
			this->groupBox_Recep->SuspendLayout();
			this->groupBox_Echantillons->SuspendLayout();
			this->groupBox_Heter->SuspendLayout();
			this->groupBox_Emis->SuspendLayout();
			this->groupBox_PLL->SuspendLayout();
			this->groupBox_Tps_mort->SuspendLayout();
			(cli::safe_cast<System::ComponentModel::ISupportInitialize^>(this->numericUpDown_Tps_mort))->BeginInit();
			this->groupBox_Bande->SuspendLayout();
			(cli::safe_cast<System::ComponentModel::ISupportInitialize^>(this->numericUpDown_Bande))->BeginInit();
			this->groupBox_Duree->SuspendLayout();
			(cli::safe_cast<System::ComponentModel::ISupportInitialize^>(this->numericUpDown_Emis))->BeginInit();
			this->groupBox_EmRec->SuspendLayout();
			this->groupBox_Periode->SuspendLayout();
			(cli::safe_cast<System::ComponentModel::ISupportInitialize^>(this->numericUpDown_Periode))->BeginInit();
			this->groupBox_Nb_Tirs->SuspendLayout();
			(cli::safe_cast<System::ComponentModel::ISupportInitialize^>(this->numericUpDown_Nb_Tirs))->BeginInit();
			(cli::safe_cast<System::ComponentModel::ISupportInitialize^>(this->pictureBox_Image))->BeginInit();
			this->groupBox_Image->SuspendLayout();
			this->groupBox_Config->SuspendLayout();
			this->SuspendLayout();
			// 
			// button_Init
			// 
			this->button_Init->Font = (gcnew System::Drawing::Font(L"Century Gothic", 16, System::Drawing::FontStyle::Bold, System::Drawing::GraphicsUnit::Point,
				static_cast<System::Byte>(0)));
			this->button_Init->Location = System::Drawing::Point(26, 24);
			this->button_Init->Margin = System::Windows::Forms::Padding(3, 4, 3, 4);
			this->button_Init->Name = L"button_Init";
			this->button_Init->Size = System::Drawing::Size(167, 52);
			this->button_Init->TabIndex = 5;
			this->button_Init->Text = L"Init USB";
			this->button_Init->UseVisualStyleBackColor = true;
			this->button_Init->Click += gcnew System::EventHandler(this, &Principale::button_Init_Click);
			// 
			// textBox_Info
			// 
			this->textBox_Info->AcceptsReturn = true;
			this->textBox_Info->Location = System::Drawing::Point(396, 12);
			this->textBox_Info->Multiline = true;
			this->textBox_Info->Name = L"textBox_Info";
			this->textBox_Info->ScrollBars = System::Windows::Forms::ScrollBars::Vertical;
			this->textBox_Info->Size = System::Drawing::Size(402, 397);
			this->textBox_Info->TabIndex = 14;
			// 
			// button_InitSigma
			// 
			this->button_InitSigma->Font = (gcnew System::Drawing::Font(L"Century Gothic", 16, System::Drawing::FontStyle::Bold, System::Drawing::GraphicsUnit::Point,
				static_cast<System::Byte>(0)));
			this->button_InitSigma->Location = System::Drawing::Point(26, 81);
			this->button_InitSigma->Margin = System::Windows::Forms::Padding(3, 4, 3, 4);
			this->button_InitSigma->Name = L"button_InitSigma";
			this->button_InitSigma->Size = System::Drawing::Size(167, 52);
			this->button_InitSigma->TabIndex = 33;
			this->button_InitSigma->Text = L"Init Sigma";
			this->button_InitSigma->UseVisualStyleBackColor = true;
			this->button_InitSigma->Click += gcnew System::EventHandler(this, &Principale::button_InitSigma_Click);
			// 
			// button_Recep
			// 
			this->button_Recep->Font = (gcnew System::Drawing::Font(L"Century Gothic", 16, System::Drawing::FontStyle::Bold, System::Drawing::GraphicsUnit::Point,
				static_cast<System::Byte>(0)));
			this->button_Recep->Location = System::Drawing::Point(204, 144);
			this->button_Recep->Margin = System::Windows::Forms::Padding(3, 4, 3, 4);
			this->button_Recep->Name = L"button_Recep";
			this->button_Recep->Size = System::Drawing::Size(167, 52);
			this->button_Recep->TabIndex = 34;
			this->button_Recep->Text = L"Reception";
			this->button_Recep->UseVisualStyleBackColor = true;
			this->button_Recep->Click += gcnew System::EventHandler(this, &Principale::button_Recep_Click);
			// 
			// button_Filtre
			// 
			this->button_Filtre->Font = (gcnew System::Drawing::Font(L"Century Gothic", 16, System::Drawing::FontStyle::Bold, System::Drawing::GraphicsUnit::Point,
				static_cast<System::Byte>(0)));
			this->button_Filtre->Location = System::Drawing::Point(204, 81);
			this->button_Filtre->Margin = System::Windows::Forms::Padding(3, 4, 3, 4);
			this->button_Filtre->Name = L"button_Filtre";
			this->button_Filtre->Size = System::Drawing::Size(167, 52);
			this->button_Filtre->TabIndex = 36;
			this->button_Filtre->Text = L"Filtre CAN";
			this->button_Filtre->UseVisualStyleBackColor = true;
			this->button_Filtre->Click += gcnew System::EventHandler(this, &Principale::button_Filtre_Click);
			// 
			// button_Reset_Altera
			// 
			this->button_Reset_Altera->Font = (gcnew System::Drawing::Font(L"Century Gothic", 16, System::Drawing::FontStyle::Bold, System::Drawing::GraphicsUnit::Point,
				static_cast<System::Byte>(0)));
			this->button_Reset_Altera->Location = System::Drawing::Point(204, 24);
			this->button_Reset_Altera->Margin = System::Windows::Forms::Padding(3, 4, 3, 4);
			this->button_Reset_Altera->Name = L"button_Reset_Altera";
			this->button_Reset_Altera->Size = System::Drawing::Size(167, 52);
			this->button_Reset_Altera->TabIndex = 38;
			this->button_Reset_Altera->Text = L"Reset Altera";
			this->button_Reset_Altera->UseVisualStyleBackColor = true;
			this->button_Reset_Altera->Click += gcnew System::EventHandler(this, &Principale::button_Reset_Altera_Click);
			// 
			// numericUpDown_Echantillons
			// 
			this->numericUpDown_Echantillons->Font = (gcnew System::Drawing::Font(L"Century Gothic", 12, System::Drawing::FontStyle::Bold, System::Drawing::GraphicsUnit::Point,
				static_cast<System::Byte>(0)));
			this->numericUpDown_Echantillons->Increment = System::Decimal(gcnew cli::array< System::Int32 >(4) { 10, 0, 0, 0 });
			this->numericUpDown_Echantillons->Location = System::Drawing::Point(17, 28);
			this->numericUpDown_Echantillons->Maximum = System::Decimal(gcnew cli::array< System::Int32 >(4) { 192, 0, 0, 0 });
			this->numericUpDown_Echantillons->Name = L"numericUpDown_Echantillons";
			this->numericUpDown_Echantillons->Size = System::Drawing::Size(65, 27);
			this->numericUpDown_Echantillons->TabIndex = 1;
			this->numericUpDown_Echantillons->ThousandsSeparator = true;
			this->numericUpDown_Echantillons->Value = System::Decimal(gcnew cli::array< System::Int32 >(4) { 24, 0, 0, 0 });
			this->numericUpDown_Echantillons->ValueChanged += gcnew System::EventHandler(this, &Principale::numericUpDown_Echantillons_ValueChanged);
			// 
			// label_Echantillons
			// 
			this->label_Echantillons->Font = (gcnew System::Drawing::Font(L"Century Gothic", 12, System::Drawing::FontStyle::Bold, System::Drawing::GraphicsUnit::Point,
				static_cast<System::Byte>(0)));
			this->label_Echantillons->Location = System::Drawing::Point(10, 21);
			this->label_Echantillons->Name = L"label_Echantillons";
			this->label_Echantillons->Size = System::Drawing::Size(135, 36);
			this->label_Echantillons->TabIndex = 2;
			this->label_Echantillons->Text = L"                   kech";
			this->label_Echantillons->TextAlign = System::Drawing::ContentAlignment::MiddleLeft;
			// 
			// label_Duree
			// 
			this->label_Duree->Dock = System::Windows::Forms::DockStyle::Bottom;
			this->label_Duree->Font = (gcnew System::Drawing::Font(L"Century Gothic", 12, System::Drawing::FontStyle::Bold, System::Drawing::GraphicsUnit::Point,
				static_cast<System::Byte>(0)));
			this->label_Duree->Location = System::Drawing::Point(3, 56);
			this->label_Duree->Name = L"label_Duree";
			this->label_Duree->Size = System::Drawing::Size(157, 27);
			this->label_Duree->TabIndex = 1;
			this->label_Duree->Text = L"61.4 ms";
			this->label_Duree->TextAlign = System::Drawing::ContentAlignment::MiddleLeft;
			// 
			// button_Emission
			// 
			this->button_Emission->Font = (gcnew System::Drawing::Font(L"Century Gothic", 16, System::Drawing::FontStyle::Bold, System::Drawing::GraphicsUnit::Point,
				static_cast<System::Byte>(0)));
			this->button_Emission->Location = System::Drawing::Point(26, 144);
			this->button_Emission->Margin = System::Windows::Forms::Padding(3, 4, 3, 4);
			this->button_Emission->Name = L"button_Emission";
			this->button_Emission->Size = System::Drawing::Size(167, 52);
			this->button_Emission->TabIndex = 42;
			this->button_Emission->Text = L"Emission";
			this->button_Emission->UseVisualStyleBackColor = true;
			this->button_Emission->Click += gcnew System::EventHandler(this, &Principale::button_Emission_Click);
			// 
			// numericUpDown_PLL
			// 
			this->numericUpDown_PLL->Font = (gcnew System::Drawing::Font(L"Century Gothic", 12, System::Drawing::FontStyle::Bold, System::Drawing::GraphicsUnit::Point,
				static_cast<System::Byte>(0)));
			this->numericUpDown_PLL->Location = System::Drawing::Point(14, 23);
			this->numericUpDown_PLL->Maximum = System::Decimal(gcnew cli::array< System::Int32 >(4) { 120, 0, 0, 0 });
			this->numericUpDown_PLL->Minimum = System::Decimal(gcnew cli::array< System::Int32 >(4) { 80, 0, 0, 0 });
			this->numericUpDown_PLL->Name = L"numericUpDown_PLL";
			this->numericUpDown_PLL->Size = System::Drawing::Size(52, 27);
			this->numericUpDown_PLL->TabIndex = 1;
			this->numericUpDown_PLL->ThousandsSeparator = true;
			this->numericUpDown_PLL->Value = System::Decimal(gcnew cli::array< System::Int32 >(4) { 100, 0, 0, 0 });
			this->numericUpDown_PLL->ValueChanged += gcnew System::EventHandler(this, &Principale::numericUpDown_PLL_ValueChanged);
			// 
			// label_PLL
			// 
			this->label_PLL->Font = (gcnew System::Drawing::Font(L"Century Gothic", 12, System::Drawing::FontStyle::Bold, System::Drawing::GraphicsUnit::Point,
				static_cast<System::Byte>(0)));
			this->label_PLL->Location = System::Drawing::Point(6, 18);
			this->label_PLL->Name = L"label_PLL";
			this->label_PLL->Size = System::Drawing::Size(96, 36);
			this->label_PLL->TabIndex = 2;
			this->label_PLL->Text = L"kHz";
			this->label_PLL->TextAlign = System::Drawing::ContentAlignment::MiddleRight;
			// 
			// listBox_NT
			// 
			this->listBox_NT->FormattingEnabled = true;
			this->listBox_NT->ItemHeight = 19;
			this->listBox_NT->Items->AddRange(gcnew cli::array< System::Object^  >(5) { L"16", L"8", L"4", L"2", L"1" });
			this->listBox_NT->Location = System::Drawing::Point(10, 31);
			this->listBox_NT->Name = L"listBox_NT";
			this->listBox_NT->Size = System::Drawing::Size(57, 23);
			this->listBox_NT->TabIndex = 3;
			this->listBox_NT->SelectedIndexChanged += gcnew System::EventHandler(this, &Principale::listBox_NT_SelectedIndexChanged);
			// 
			// label_NT
			// 
			this->label_NT->Font = (gcnew System::Drawing::Font(L"Century Gothic", 12, System::Drawing::FontStyle::Bold, System::Drawing::GraphicsUnit::Point,
				static_cast<System::Byte>(0)));
			this->label_NT->Location = System::Drawing::Point(6, 23);
			this->label_NT->Name = L"label_NT";
			this->label_NT->Size = System::Drawing::Size(151, 36);
			this->label_NT->TabIndex = 2;
			this->label_NT->Text = L"                 p�riodes";
			this->label_NT->TextAlign = System::Drawing::ContentAlignment::MiddleLeft;
			// 
			// button_Start
			// 
			this->button_Start->Font = (gcnew System::Drawing::Font(L"Century Gothic", 16, System::Drawing::FontStyle::Bold, System::Drawing::GraphicsUnit::Point,
				static_cast<System::Byte>(0)));
			this->button_Start->Location = System::Drawing::Point(27, 47);
			this->button_Start->Margin = System::Windows::Forms::Padding(3, 4, 3, 4);
			this->button_Start->Name = L"button_Start";
			this->button_Start->Size = System::Drawing::Size(167, 52);
			this->button_Start->TabIndex = 45;
			this->button_Start->Text = L"Start";
			this->button_Start->UseVisualStyleBackColor = true;
			this->button_Start->Click += gcnew System::EventHandler(this, &Principale::button_Em_Rec_Click);
			// 
			// groupBox_Test
			// 
			this->groupBox_Test->Controls->Add(this->button_InitSigma);
			this->groupBox_Test->Controls->Add(this->button_Recep);
			this->groupBox_Test->Controls->Add(this->button_Filtre);
			this->groupBox_Test->Controls->Add(this->button_Reset_Altera);
			this->groupBox_Test->Controls->Add(this->button_Initialisation);
			this->groupBox_Test->Controls->Add(this->button_Image);
			this->groupBox_Test->Controls->Add(this->button_Emission);
			this->groupBox_Test->Controls->Add(this->button_Init);
			this->groupBox_Test->Font = (gcnew System::Drawing::Font(L"Century Gothic", 14, System::Drawing::FontStyle::Bold, System::Drawing::GraphicsUnit::Point,
				static_cast<System::Byte>(0)));
			this->groupBox_Test->Location = System::Drawing::Point(396, 415);
			this->groupBox_Test->Name = L"groupBox_Test";
			this->groupBox_Test->Size = System::Drawing::Size(388, 288);
			this->groupBox_Test->TabIndex = 46;
			this->groupBox_Test->TabStop = false;
			this->groupBox_Test->Text = L"Test";
			this->groupBox_Test->Visible = false;
			// 
			// button_Initialisation
			// 
			this->button_Initialisation->Font = (gcnew System::Drawing::Font(L"Century Gothic", 16, System::Drawing::FontStyle::Bold, System::Drawing::GraphicsUnit::Point,
				static_cast<System::Byte>(0)));
			this->button_Initialisation->Location = System::Drawing::Point(26, 204);
			this->button_Initialisation->Margin = System::Windows::Forms::Padding(3, 4, 3, 4);
			this->button_Initialisation->Name = L"button_Initialisation";
			this->button_Initialisation->Size = System::Drawing::Size(167, 52);
			this->button_Initialisation->TabIndex = 49;
			this->button_Initialisation->Text = L"Initialisation";
			this->button_Initialisation->UseVisualStyleBackColor = true;
			this->button_Initialisation->Click += gcnew System::EventHandler(this, &Principale::button_Initialisation_Click);
			// 
			// button_Image
			// 
			this->button_Image->Font = (gcnew System::Drawing::Font(L"Century Gothic", 16, System::Drawing::FontStyle::Bold, System::Drawing::GraphicsUnit::Point,
				static_cast<System::Byte>(0)));
			this->button_Image->Location = System::Drawing::Point(204, 204);
			this->button_Image->Margin = System::Windows::Forms::Padding(3, 4, 3, 4);
			this->button_Image->Name = L"button_Image";
			this->button_Image->Size = System::Drawing::Size(167, 52);
			this->button_Image->TabIndex = 51;
			this->button_Image->Text = L"Image";
			this->button_Image->UseVisualStyleBackColor = true;
			this->button_Image->Click += gcnew System::EventHandler(this, &Principale::button_Image_Click);
			// 
			// checkBox_Test
			// 
			this->checkBox_Test->AutoSize = true;
			this->checkBox_Test->Font = (gcnew System::Drawing::Font(L"Century Gothic", 14, System::Drawing::FontStyle::Bold, System::Drawing::GraphicsUnit::Point,
				static_cast<System::Byte>(0)));
			this->checkBox_Test->Location = System::Drawing::Point(14, 717);
			this->checkBox_Test->Name = L"checkBox_Test";
			this->checkBox_Test->Size = System::Drawing::Size(63, 27);
			this->checkBox_Test->TabIndex = 50;
			this->checkBox_Test->Text = L"Test";
			this->checkBox_Test->UseVisualStyleBackColor = true;
			this->checkBox_Test->CheckedChanged += gcnew System::EventHandler(this, &Principale::checkBox_Test_CheckedChanged);
			// 
			// groupBox_Recep
			// 
			this->groupBox_Recep->Controls->Add(this->groupBox_Echantillons);
			this->groupBox_Recep->Controls->Add(this->groupBox_Heter);
			this->groupBox_Recep->Dock = System::Windows::Forms::DockStyle::Bottom;
			this->groupBox_Recep->Font = (gcnew System::Drawing::Font(L"Century Gothic", 14, System::Drawing::FontStyle::Bold, System::Drawing::GraphicsUnit::Point,
				static_cast<System::Byte>(0)));
			this->groupBox_Recep->Location = System::Drawing::Point(3, 320);
			this->groupBox_Recep->Name = L"groupBox_Recep";
			this->groupBox_Recep->Size = System::Drawing::Size(371, 127);
			this->groupBox_Recep->TabIndex = 47;
			this->groupBox_Recep->TabStop = false;
			this->groupBox_Recep->Text = L"R�ception";
			// 
			// groupBox_Echantillons
			// 
			this->groupBox_Echantillons->Controls->Add(this->numericUpDown_Echantillons);
			this->groupBox_Echantillons->Controls->Add(this->label_Echantillons);
			this->groupBox_Echantillons->Controls->Add(this->label_Duree);
			this->groupBox_Echantillons->Font = (gcnew System::Drawing::Font(L"Century Gothic", 12, System::Drawing::FontStyle::Bold, System::Drawing::GraphicsUnit::Point,
				static_cast<System::Byte>(0)));
			this->groupBox_Echantillons->Location = System::Drawing::Point(188, 31);
			this->groupBox_Echantillons->Name = L"groupBox_Echantillons";
			this->groupBox_Echantillons->Size = System::Drawing::Size(163, 86);
			this->groupBox_Echantillons->TabIndex = 46;
			this->groupBox_Echantillons->TabStop = false;
			this->groupBox_Echantillons->Text = L"Dur�e";
			// 
			// groupBox_Heter
			// 
			this->groupBox_Heter->Controls->Add(this->listBox_NT);
			this->groupBox_Heter->Controls->Add(this->label_NT);
			this->groupBox_Heter->Font = (gcnew System::Drawing::Font(L"Century Gothic", 12, System::Drawing::FontStyle::Bold, System::Drawing::GraphicsUnit::Point,
				static_cast<System::Byte>(0)));
			this->groupBox_Heter->Location = System::Drawing::Point(10, 31);
			this->groupBox_Heter->Name = L"groupBox_Heter";
			this->groupBox_Heter->Size = System::Drawing::Size(163, 66);
			this->groupBox_Heter->TabIndex = 45;
			this->groupBox_Heter->TabStop = false;
			this->groupBox_Heter->Text = L"H�t�rodynage";
			// 
			// groupBox_Emis
			// 
			this->groupBox_Emis->Controls->Add(this->groupBox_PLL);
			this->groupBox_Emis->Controls->Add(this->groupBox_Tps_mort);
			this->groupBox_Emis->Controls->Add(this->groupBox_Bande);
			this->groupBox_Emis->Controls->Add(this->groupBox_Duree);
			this->groupBox_Emis->Dock = System::Windows::Forms::DockStyle::Bottom;
			this->groupBox_Emis->FlatStyle = System::Windows::Forms::FlatStyle::Flat;
			this->groupBox_Emis->Font = (gcnew System::Drawing::Font(L"Century Gothic", 14, System::Drawing::FontStyle::Bold, System::Drawing::GraphicsUnit::Point,
				static_cast<System::Byte>(0)));
			this->groupBox_Emis->Location = System::Drawing::Point(3, 113);
			this->groupBox_Emis->Name = L"groupBox_Emis";
			this->groupBox_Emis->Size = System::Drawing::Size(371, 207);
			this->groupBox_Emis->TabIndex = 48;
			this->groupBox_Emis->TabStop = false;
			this->groupBox_Emis->Text = L"Emission";
			// 
			// groupBox_PLL
			// 
			this->groupBox_PLL->Controls->Add(this->numericUpDown_PLL);
			this->groupBox_PLL->Controls->Add(this->label_PLL);
			this->groupBox_PLL->Font = (gcnew System::Drawing::Font(L"Century Gothic", 12, System::Drawing::FontStyle::Bold, System::Drawing::GraphicsUnit::Point,
				static_cast<System::Byte>(0)));
			this->groupBox_PLL->Location = System::Drawing::Point(7, 29);
			this->groupBox_PLL->Name = L"groupBox_PLL";
			this->groupBox_PLL->Size = System::Drawing::Size(166, 60);
			this->groupBox_PLL->TabIndex = 49;
			this->groupBox_PLL->TabStop = false;
			this->groupBox_PLL->Text = L"Freq. centrale";
			// 
			// groupBox_Tps_mort
			// 
			this->groupBox_Tps_mort->Controls->Add(this->numericUpDown_Tps_mort);
			this->groupBox_Tps_mort->Controls->Add(this->label_Tps_mort);
			this->groupBox_Tps_mort->Controls->Add(this->label3);
			this->groupBox_Tps_mort->Font = (gcnew System::Drawing::Font(L"Century Gothic", 12, System::Drawing::FontStyle::Bold, System::Drawing::GraphicsUnit::Point,
				static_cast<System::Byte>(0)));
			this->groupBox_Tps_mort->Location = System::Drawing::Point(179, 95);
			this->groupBox_Tps_mort->Name = L"groupBox_Tps_mort";
			this->groupBox_Tps_mort->Size = System::Drawing::Size(172, 103);
			this->groupBox_Tps_mort->TabIndex = 49;
			this->groupBox_Tps_mort->TabStop = false;
			this->groupBox_Tps_mort->Text = L"Temps mort";
			// 
			// numericUpDown_Tps_mort
			// 
			this->numericUpDown_Tps_mort->Font = (gcnew System::Drawing::Font(L"Century Gothic", 12, System::Drawing::FontStyle::Bold, System::Drawing::GraphicsUnit::Point,
				static_cast<System::Byte>(0)));
			this->numericUpDown_Tps_mort->Location = System::Drawing::Point(9, 30);
			this->numericUpDown_Tps_mort->Maximum = System::Decimal(gcnew cli::array< System::Int32 >(4) { 200, 0, 0, 0 });
			this->numericUpDown_Tps_mort->Minimum = System::Decimal(gcnew cli::array< System::Int32 >(4) { 1, 0, 0, 0 });
			this->numericUpDown_Tps_mort->Name = L"numericUpDown_Tps_mort";
			this->numericUpDown_Tps_mort->Size = System::Drawing::Size(65, 27);
			this->numericUpDown_Tps_mort->TabIndex = 3;
			this->numericUpDown_Tps_mort->ThousandsSeparator = true;
			this->numericUpDown_Tps_mort->Value = System::Decimal(gcnew cli::array< System::Int32 >(4) { 10, 0, 0, 0 });
			this->numericUpDown_Tps_mort->ValueChanged += gcnew System::EventHandler(this, &Principale::numericUpDown_Tps_mort_ValueChanged);
			// 
			// label_Tps_mort
			// 
			this->label_Tps_mort->Font = (gcnew System::Drawing::Font(L"Century Gothic", 12, System::Drawing::FontStyle::Bold, System::Drawing::GraphicsUnit::Point,
				static_cast<System::Byte>(0)));
			this->label_Tps_mort->Location = System::Drawing::Point(7, 59);
			this->label_Tps_mort->Name = L"label_Tps_mort";
			this->label_Tps_mort->Size = System::Drawing::Size(137, 40);
			this->label_Tps_mort->TabIndex = 46;
			this->label_Tps_mort->Text = L"Dur�e : 0.1 ms";
			this->label_Tps_mort->TextAlign = System::Drawing::ContentAlignment::MiddleLeft;
			// 
			// label3
			// 
			this->label3->Font = (gcnew System::Drawing::Font(L"Century Gothic", 12, System::Drawing::FontStyle::Bold, System::Drawing::GraphicsUnit::Point,
				static_cast<System::Byte>(0)));
			this->label3->Location = System::Drawing::Point(6, 23);
			this->label3->Name = L"label3";
			this->label3->Size = System::Drawing::Size(145, 36);
			this->label3->TabIndex = 2;
			this->label3->Text = L"                 p�riodes";
			this->label3->TextAlign = System::Drawing::ContentAlignment::MiddleLeft;
			// 
			// groupBox_Bande
			// 
			this->groupBox_Bande->Controls->Add(this->numericUpDown_Bande);
			this->groupBox_Bande->Controls->Add(this->label_Bande);
			this->groupBox_Bande->Font = (gcnew System::Drawing::Font(L"Century Gothic", 12, System::Drawing::FontStyle::Bold, System::Drawing::GraphicsUnit::Point,
				static_cast<System::Byte>(0)));
			this->groupBox_Bande->Location = System::Drawing::Point(179, 29);
			this->groupBox_Bande->Name = L"groupBox_Bande";
			this->groupBox_Bande->Size = System::Drawing::Size(172, 60);
			this->groupBox_Bande->TabIndex = 48;
			this->groupBox_Bande->TabStop = false;
			this->groupBox_Bande->Text = L"Bande";
			// 
			// numericUpDown_Bande
			// 
			this->numericUpDown_Bande->DecimalPlaces = 1;
			this->numericUpDown_Bande->Font = (gcnew System::Drawing::Font(L"Century Gothic", 12, System::Drawing::FontStyle::Bold, System::Drawing::GraphicsUnit::Point,
				static_cast<System::Byte>(0)));
			this->numericUpDown_Bande->Location = System::Drawing::Point(9, 25);
			this->numericUpDown_Bande->Maximum = System::Decimal(gcnew cli::array< System::Int32 >(4) { 40, 0, 0, 0 });
			this->numericUpDown_Bande->Name = L"numericUpDown_Bande";
			this->numericUpDown_Bande->Size = System::Drawing::Size(65, 27);
			this->numericUpDown_Bande->TabIndex = 3;
			this->numericUpDown_Bande->ThousandsSeparator = true;
			this->numericUpDown_Bande->ValueChanged += gcnew System::EventHandler(this, &Principale::numericUpDown_Bande_ValueChanged);
			// 
			// label_Bande
			// 
			this->label_Bande->Font = (gcnew System::Drawing::Font(L"Century Gothic", 12, System::Drawing::FontStyle::Bold, System::Drawing::GraphicsUnit::Point,
				static_cast<System::Byte>(0)));
			this->label_Bande->Location = System::Drawing::Point(6, 18);
			this->label_Bande->Name = L"label_Bande";
			this->label_Bande->Size = System::Drawing::Size(120, 36);
			this->label_Bande->TabIndex = 2;
			this->label_Bande->Text = L"                 kHz";
			this->label_Bande->TextAlign = System::Drawing::ContentAlignment::MiddleLeft;
			// 
			// groupBox_Duree
			// 
			this->groupBox_Duree->Controls->Add(this->numericUpDown_Emis);
			this->groupBox_Duree->Controls->Add(this->label_Emis);
			this->groupBox_Duree->Controls->Add(this->label_D_Emis);
			this->groupBox_Duree->Font = (gcnew System::Drawing::Font(L"Century Gothic", 12, System::Drawing::FontStyle::Bold, System::Drawing::GraphicsUnit::Point,
				static_cast<System::Byte>(0)));
			this->groupBox_Duree->Location = System::Drawing::Point(6, 95);
			this->groupBox_Duree->Name = L"groupBox_Duree";
			this->groupBox_Duree->Size = System::Drawing::Size(163, 103);
			this->groupBox_Duree->TabIndex = 47;
			this->groupBox_Duree->TabStop = false;
			this->groupBox_Duree->Text = L"Dur�e";
			// 
			// numericUpDown_Emis
			// 
			this->numericUpDown_Emis->Font = (gcnew System::Drawing::Font(L"Century Gothic", 12, System::Drawing::FontStyle::Bold, System::Drawing::GraphicsUnit::Point,
				static_cast<System::Byte>(0)));
			this->numericUpDown_Emis->Location = System::Drawing::Point(9, 30);
			this->numericUpDown_Emis->Maximum = System::Decimal(gcnew cli::array< System::Int32 >(4) { 200, 0, 0, 0 });
			this->numericUpDown_Emis->Minimum = System::Decimal(gcnew cli::array< System::Int32 >(4) { 1, 0, 0, 0 });
			this->numericUpDown_Emis->Name = L"numericUpDown_Emis";
			this->numericUpDown_Emis->Size = System::Drawing::Size(65, 27);
			this->numericUpDown_Emis->TabIndex = 3;
			this->numericUpDown_Emis->ThousandsSeparator = true;
			this->numericUpDown_Emis->Value = System::Decimal(gcnew cli::array< System::Int32 >(4) { 10, 0, 0, 0 });
			this->numericUpDown_Emis->ValueChanged += gcnew System::EventHandler(this, &Principale::numericUpDown_Emis_ValueChanged);
			// 
			// label_Emis
			// 
			this->label_Emis->Font = (gcnew System::Drawing::Font(L"Century Gothic", 12, System::Drawing::FontStyle::Bold, System::Drawing::GraphicsUnit::Point,
				static_cast<System::Byte>(0)));
			this->label_Emis->Location = System::Drawing::Point(7, 59);
			this->label_Emis->Name = L"label_Emis";
			this->label_Emis->Size = System::Drawing::Size(150, 40);
			this->label_Emis->TabIndex = 46;
			this->label_Emis->Text = L"Dur�e : 0.1 ms";
			this->label_Emis->TextAlign = System::Drawing::ContentAlignment::MiddleLeft;
			// 
			// label_D_Emis
			// 
			this->label_D_Emis->Font = (gcnew System::Drawing::Font(L"Century Gothic", 12, System::Drawing::FontStyle::Bold, System::Drawing::GraphicsUnit::Point,
				static_cast<System::Byte>(0)));
			this->label_D_Emis->Location = System::Drawing::Point(6, 23);
			this->label_D_Emis->Name = L"label_D_Emis";
			this->label_D_Emis->Size = System::Drawing::Size(146, 36);
			this->label_D_Emis->TabIndex = 2;
			this->label_D_Emis->Text = L"                 p�riodes";
			this->label_D_Emis->TextAlign = System::Drawing::ContentAlignment::MiddleLeft;
			// 
			// groupBox_EmRec
			// 
			this->groupBox_EmRec->Controls->Add(this->button_Fichier);
			this->groupBox_EmRec->Controls->Add(this->groupBox_Periode);
			this->groupBox_EmRec->Controls->Add(this->groupBox_Nb_Tirs);
			this->groupBox_EmRec->Controls->Add(this->button_Eff_Image);
			this->groupBox_EmRec->Controls->Add(this->button_Stop);
			this->groupBox_EmRec->Controls->Add(this->button_Start);
			this->groupBox_EmRec->Font = (gcnew System::Drawing::Font(L"Century Gothic", 14, System::Drawing::FontStyle::Bold, System::Drawing::GraphicsUnit::Point,
				static_cast<System::Byte>(0)));
			this->groupBox_EmRec->Location = System::Drawing::Point(14, 471);
			this->groupBox_EmRec->Name = L"groupBox_EmRec";
			this->groupBox_EmRec->Size = System::Drawing::Size(376, 232);
			this->groupBox_EmRec->TabIndex = 48;
			this->groupBox_EmRec->TabStop = false;
			this->groupBox_EmRec->Text = L"Emission/R�ception";
			// 
			// button_Fichier
			// 
			this->button_Fichier->Font = (gcnew System::Drawing::Font(L"Century Gothic", 16, System::Drawing::FontStyle::Bold, System::Drawing::GraphicsUnit::Point,
				static_cast<System::Byte>(0)));
			this->button_Fichier->Location = System::Drawing::Point(27, 167);
			this->button_Fichier->Margin = System::Windows::Forms::Padding(3, 4, 3, 4);
			this->button_Fichier->Name = L"button_Fichier";
			this->button_Fichier->Size = System::Drawing::Size(167, 52);
			this->button_Fichier->TabIndex = 52;
			this->button_Fichier->Text = L"Choix fichier";
			this->button_Fichier->UseVisualStyleBackColor = true;
			this->button_Fichier->Click += gcnew System::EventHandler(this, &Principale::button_Fichier_Click);
			// 
			// groupBox_Periode
			// 
			this->groupBox_Periode->Controls->Add(this->numericUpDown_Periode);
			this->groupBox_Periode->Controls->Add(this->label_Periode);
			this->groupBox_Periode->Font = (gcnew System::Drawing::Font(L"Century Gothic", 12, System::Drawing::FontStyle::Bold, System::Drawing::GraphicsUnit::Point,
				static_cast<System::Byte>(0)));
			this->groupBox_Periode->Location = System::Drawing::Point(210, 101);
			this->groupBox_Periode->Name = L"groupBox_Periode";
			this->groupBox_Periode->Size = System::Drawing::Size(121, 52);
			this->groupBox_Periode->TabIndex = 51;
			this->groupBox_Periode->TabStop = false;
			this->groupBox_Periode->Text = L"P�riode";
			// 
			// numericUpDown_Periode
			// 
			this->numericUpDown_Periode->Dock = System::Windows::Forms::DockStyle::Left;
			this->numericUpDown_Periode->Font = (gcnew System::Drawing::Font(L"Century Gothic", 12, System::Drawing::FontStyle::Bold, System::Drawing::GraphicsUnit::Point,
				static_cast<System::Byte>(0)));
			this->numericUpDown_Periode->Increment = System::Decimal(gcnew cli::array< System::Int32 >(4) { 100, 0, 0, 0 });
			this->numericUpDown_Periode->Location = System::Drawing::Point(3, 23);
			this->numericUpDown_Periode->Maximum = System::Decimal(gcnew cli::array< System::Int32 >(4) { 2000, 0, 0, 0 });
			this->numericUpDown_Periode->Name = L"numericUpDown_Periode";
			this->numericUpDown_Periode->Size = System::Drawing::Size(65, 27);
			this->numericUpDown_Periode->TabIndex = 47;
			this->numericUpDown_Periode->ThousandsSeparator = true;
			this->numericUpDown_Periode->Value = System::Decimal(gcnew cli::array< System::Int32 >(4) { 250, 0, 0, 0 });
			// 
			// label_Periode
			// 
			this->label_Periode->Dock = System::Windows::Forms::DockStyle::Bottom;
			this->label_Periode->Font = (gcnew System::Drawing::Font(L"Century Gothic", 12, System::Drawing::FontStyle::Bold, System::Drawing::GraphicsUnit::Point,
				static_cast<System::Byte>(0)));
			this->label_Periode->Location = System::Drawing::Point(3, 23);
			this->label_Periode->Name = L"label_Periode";
			this->label_Periode->Size = System::Drawing::Size(115, 26);
			this->label_Periode->TabIndex = 46;
			this->label_Periode->Text = L"                 ms";
			this->label_Periode->TextAlign = System::Drawing::ContentAlignment::MiddleLeft;
			// 
			// groupBox_Nb_Tirs
			// 
			this->groupBox_Nb_Tirs->Controls->Add(this->numericUpDown_Nb_Tirs);
			this->groupBox_Nb_Tirs->Controls->Add(this->label_Nb_Tirs);
			this->groupBox_Nb_Tirs->Font = (gcnew System::Drawing::Font(L"Century Gothic", 12, System::Drawing::FontStyle::Bold, System::Drawing::GraphicsUnit::Point,
				static_cast<System::Byte>(0)));
			this->groupBox_Nb_Tirs->Location = System::Drawing::Point(210, 43);
			this->groupBox_Nb_Tirs->Name = L"groupBox_Nb_Tirs";
			this->groupBox_Nb_Tirs->Size = System::Drawing::Size(121, 52);
			this->groupBox_Nb_Tirs->TabIndex = 50;
			this->groupBox_Nb_Tirs->TabStop = false;
			this->groupBox_Nb_Tirs->Text = L"Nb tirs";
			// 
			// numericUpDown_Nb_Tirs
			// 
			this->numericUpDown_Nb_Tirs->Dock = System::Windows::Forms::DockStyle::Left;
			this->numericUpDown_Nb_Tirs->Font = (gcnew System::Drawing::Font(L"Century Gothic", 12, System::Drawing::FontStyle::Bold, System::Drawing::GraphicsUnit::Point,
				static_cast<System::Byte>(0)));
			this->numericUpDown_Nb_Tirs->Location = System::Drawing::Point(3, 23);
			this->numericUpDown_Nb_Tirs->Maximum = System::Decimal(gcnew cli::array< System::Int32 >(4) { 200, 0, 0, 0 });
			this->numericUpDown_Nb_Tirs->Name = L"numericUpDown_Nb_Tirs";
			this->numericUpDown_Nb_Tirs->Size = System::Drawing::Size(65, 27);
			this->numericUpDown_Nb_Tirs->TabIndex = 47;
			this->numericUpDown_Nb_Tirs->ThousandsSeparator = true;
			this->numericUpDown_Nb_Tirs->Value = System::Decimal(gcnew cli::array< System::Int32 >(4) { 10, 0, 0, 0 });
			// 
			// label_Nb_Tirs
			// 
			this->label_Nb_Tirs->Dock = System::Windows::Forms::DockStyle::Bottom;
			this->label_Nb_Tirs->Font = (gcnew System::Drawing::Font(L"Century Gothic", 12, System::Drawing::FontStyle::Bold, System::Drawing::GraphicsUnit::Point,
				static_cast<System::Byte>(0)));
			this->label_Nb_Tirs->Location = System::Drawing::Point(3, 23);
			this->label_Nb_Tirs->Name = L"label_Nb_Tirs";
			this->label_Nb_Tirs->Size = System::Drawing::Size(115, 26);
			this->label_Nb_Tirs->TabIndex = 46;
			this->label_Nb_Tirs->Text = L"                 tirs";
			this->label_Nb_Tirs->TextAlign = System::Drawing::ContentAlignment::MiddleLeft;
			// 
			// button_Eff_Image
			// 
			this->button_Eff_Image->Font = (gcnew System::Drawing::Font(L"Century Gothic", 16, System::Drawing::FontStyle::Bold, System::Drawing::GraphicsUnit::Point,
				static_cast<System::Byte>(0)));
			this->button_Eff_Image->Location = System::Drawing::Point(203, 167);
			this->button_Eff_Image->Margin = System::Windows::Forms::Padding(3, 4, 3, 4);
			this->button_Eff_Image->Name = L"button_Eff_Image";
			this->button_Eff_Image->Size = System::Drawing::Size(167, 52);
			this->button_Eff_Image->TabIndex = 54;
			this->button_Eff_Image->Text = L"Efface Image";
			this->button_Eff_Image->UseVisualStyleBackColor = true;
			this->button_Eff_Image->Click += gcnew System::EventHandler(this, &Principale::button_Eff_Image_Click);
			// 
			// button_Stop
			// 
			this->button_Stop->Font = (gcnew System::Drawing::Font(L"Century Gothic", 16, System::Drawing::FontStyle::Bold, System::Drawing::GraphicsUnit::Point,
				static_cast<System::Byte>(0)));
			this->button_Stop->Location = System::Drawing::Point(27, 107);
			this->button_Stop->Margin = System::Windows::Forms::Padding(3, 4, 3, 4);
			this->button_Stop->Name = L"button_Stop";
			this->button_Stop->Size = System::Drawing::Size(167, 52);
			this->button_Stop->TabIndex = 48;
			this->button_Stop->Text = L"Stop";
			this->button_Stop->UseVisualStyleBackColor = true;
			this->button_Stop->Visible = false;
			this->button_Stop->Click += gcnew System::EventHandler(this, &Principale::button_Stop_Click);
			// 
			// saveFileDialog_Data
			// 
			this->saveFileDialog_Data->Filter = L"data |*.dat";
			// 
			// pictureBox_Image
			// 
			this->pictureBox_Image->BackColor = System::Drawing::Color::Black;
			this->pictureBox_Image->Dock = System::Windows::Forms::DockStyle::Left;
			this->pictureBox_Image->Location = System::Drawing::Point(3, 17);
			this->pictureBox_Image->Name = L"pictureBox_Image";
			this->pictureBox_Image->Size = System::Drawing::Size(596, 729);
			this->pictureBox_Image->TabIndex = 50;
			this->pictureBox_Image->TabStop = false;
			// 
			// vScrollBar_Image
			// 
			this->vScrollBar_Image->Dock = System::Windows::Forms::DockStyle::Right;
			this->vScrollBar_Image->Enabled = false;
			this->vScrollBar_Image->LargeChange = 50;
			this->vScrollBar_Image->Location = System::Drawing::Point(603, 17);
			this->vScrollBar_Image->Margin = System::Windows::Forms::Padding(1);
			this->vScrollBar_Image->Maximum = 733;
			this->vScrollBar_Image->Name = L"vScrollBar_Image";
			this->vScrollBar_Image->Size = System::Drawing::Size(18, 729);
			this->vScrollBar_Image->TabIndex = 52;
			this->vScrollBar_Image->Scroll += gcnew System::Windows::Forms::ScrollEventHandler(this, &Principale::vScrollBar_Image_Scroll);
			// 
			// groupBox_Image
			// 
			this->groupBox_Image->BackColor = System::Drawing::Color::White;
			this->groupBox_Image->Controls->Add(this->vScrollBar_Image);
			this->groupBox_Image->Controls->Add(this->pictureBox_Image);
			this->groupBox_Image->Dock = System::Windows::Forms::DockStyle::Right;
			this->groupBox_Image->Location = System::Drawing::Point(809, 0);
			this->groupBox_Image->Name = L"groupBox_Image";
			this->groupBox_Image->Size = System::Drawing::Size(624, 749);
			this->groupBox_Image->TabIndex = 53;
			this->groupBox_Image->TabStop = false;
			// 
			// groupBox_Config
			// 
			this->groupBox_Config->Controls->Add(this->groupBox_Emis);
			this->groupBox_Config->Controls->Add(this->button_Config);
			this->groupBox_Config->Controls->Add(this->groupBox_Recep);
			this->groupBox_Config->Font = (gcnew System::Drawing::Font(L"Century Gothic", 16, System::Drawing::FontStyle::Bold, System::Drawing::GraphicsUnit::Point,
				static_cast<System::Byte>(0)));
			this->groupBox_Config->Location = System::Drawing::Point(13, 12);
			this->groupBox_Config->Name = L"groupBox_Config";
			this->groupBox_Config->Size = System::Drawing::Size(377, 450);
			this->groupBox_Config->TabIndex = 55;
			this->groupBox_Config->TabStop = false;
			this->groupBox_Config->Text = L"Configuration";
			// 
			// button_Config
			// 
			this->button_Config->Font = (gcnew System::Drawing::Font(L"Century Gothic", 16, System::Drawing::FontStyle::Bold, System::Drawing::GraphicsUnit::Point,
				static_cast<System::Byte>(0)));
			this->button_Config->Location = System::Drawing::Point(10, 49);
			this->button_Config->Margin = System::Windows::Forms::Padding(3, 4, 3, 4);
			this->button_Config->Name = L"button_Config";
			this->button_Config->Size = System::Drawing::Size(167, 52);
			this->button_Config->TabIndex = 56;
			this->button_Config->Text = L"Configuration";
			this->button_Config->UseVisualStyleBackColor = true;
			this->button_Config->Click += gcnew System::EventHandler(this, &Principale::button_Config_Click);
			// 
			// Principale
			// 
			this->AutoScaleDimensions = System::Drawing::SizeF(7, 16);
			this->AutoScaleMode = System::Windows::Forms::AutoScaleMode::Font;
			this->AutoScroll = true;
			this->ClientSize = System::Drawing::Size(1433, 749);
			this->Controls->Add(this->checkBox_Test);
			this->Controls->Add(this->groupBox_Config);
			this->Controls->Add(this->groupBox_Image);
			this->Controls->Add(this->textBox_Info);
			this->Controls->Add(this->groupBox_EmRec);
			this->Controls->Add(this->groupBox_Test);
			this->Font = (gcnew System::Drawing::Font(L"Century Gothic", 8.25F, System::Drawing::FontStyle::Regular, System::Drawing::GraphicsUnit::Point,
				static_cast<System::Byte>(0)));
			this->Margin = System::Windows::Forms::Padding(3, 4, 3, 4);
			this->MaximizeBox = false;
			this->Name = L"Principale";
			this->StartPosition = System::Windows::Forms::FormStartPosition::Manual;
			this->Text = L"SLBP V4 mai 2019";
			(cli::safe_cast<System::ComponentModel::ISupportInitialize^>(this->numericUpDown_Echantillons))->EndInit();
			(cli::safe_cast<System::ComponentModel::ISupportInitialize^>(this->numericUpDown_PLL))->EndInit();
			this->groupBox_Test->ResumeLayout(false);
			this->groupBox_Recep->ResumeLayout(false);
			this->groupBox_Echantillons->ResumeLayout(false);
			this->groupBox_Heter->ResumeLayout(false);
			this->groupBox_Emis->ResumeLayout(false);
			this->groupBox_PLL->ResumeLayout(false);
			this->groupBox_Tps_mort->ResumeLayout(false);
			(cli::safe_cast<System::ComponentModel::ISupportInitialize^>(this->numericUpDown_Tps_mort))->EndInit();
			this->groupBox_Bande->ResumeLayout(false);
			(cli::safe_cast<System::ComponentModel::ISupportInitialize^>(this->numericUpDown_Bande))->EndInit();
			this->groupBox_Duree->ResumeLayout(false);
			(cli::safe_cast<System::ComponentModel::ISupportInitialize^>(this->numericUpDown_Emis))->EndInit();
			this->groupBox_EmRec->ResumeLayout(false);
			this->groupBox_Periode->ResumeLayout(false);
			(cli::safe_cast<System::ComponentModel::ISupportInitialize^>(this->numericUpDown_Periode))->EndInit();
			this->groupBox_Nb_Tirs->ResumeLayout(false);
			(cli::safe_cast<System::ComponentModel::ISupportInitialize^>(this->numericUpDown_Nb_Tirs))->EndInit();
			(cli::safe_cast<System::ComponentModel::ISupportInitialize^>(this->pictureBox_Image))->EndInit();
			this->groupBox_Image->ResumeLayout(false);
			this->groupBox_Config->ResumeLayout(false);
			this->ResumeLayout(false);
			this->PerformLayout();

		}
#pragma endregion

	private: System::Void button_Init_Click(System::Object^  sender, System::EventArgs^  e)
	{
		init_FX3();
	}
	private: System::Void button_InitSigma_Click(System::Object^  sender, System::EventArgs^  e)
	{
		int r;
		if (!init_USB)
		{
			call_verb("Pas de liaison USB !\n", 1);
			return;
		}
		r = write_command(handle, C_INIT_SIGMA, buf, 0); //envoi de la commande d'initialisation du convertisseur
		if (r) call_verb(String::Format("Erreur initialisation sigma-delta retour: {0:G} \n", r), 0);
		else if (test) call_verb("Initialisation sigma-delta\n", 0);
	}
	private: System::Void button_Recep_Click(System::Object^  sender, System::EventArgs^  e)
	{// on passe nb_echant+1
		int r, nb_ecrit, rc = LIBUSB_SUCCESS, TAILLE;
		unsigned long int j;
		unsigned char *p;
		if (!init_USB)
		{
			call_verb("Pas de liaison USB !\n", 1);
			return;
		}

		if (!PLL_Init) numericUpDown_PLL_ValueChanged(this, e);
		// R�cup�ration des donn�es h�t�rodyn�es � travers une t�che fond ex�cut�e une fois
		NT = NT_VAL[listBox_NT->TopIndex];
		buf[4] = (NT & 0x00ff);
		nb_echant = (unsigned long)(Decimal::ToDouble(numericUpDown_Echantillons->Value) * 1024) + 1;
		buf[3] = (nb_echant & 0x000000ff);
		buf[2] = (nb_echant & 0x0000ff00) >> 8;
		buf[1] = (nb_echant & 0x00ff0000) >> 16;
		buf[0] = (nb_echant & 0xff000000) >> 24;
		nb_echant -= 1;
	
		// initialisation de la t�che de fond
		TAILLE = (int)(((long)nb_echant) * 8 / RF / NT); //Attention max : 0x60000 octets
		callback = (libusb_transfer_cb_fn)fn_callback;
		transfert = libusb_alloc_transfer(0);
		buffers = new unsigned char[TAILLE];
		libusb_fill_bulk_transfer(transfert, handle, _ADDR_LECT, buffers, TAILLE, callback, NULL, TimeOut);

		if (test) Fich_test = fopen("init.dat0", "wb");
		Rec_Init = false;
		transfert_fini = false;
		r = write_command(handle, C_RECEP, buf, 0); //envoi de la commande de r�ception
		r = libusb_bulk_transfer(handle, _ADDR_ECR, &(buf[0]), 5, &nb_ecrit, TimeOut); //envoi des param�tres
		if (r) call_verb(String::Format("Erreur d�clenchement de la r�ception retour: {0:G} \n", r), 0);
		else if (checkBox_Test->Checked) call_verb(String::Format("D�clenchement de la r�ception, NT = {0:G}  Transfert de {1:G} octets\n", NT,TAILLE), 0);
		
		retour = libusb_submit_transfer(transfert); //lancement t�che de fond
		if (retour)
		{
			call_verb("Erreur lancement transfert \n", 0);
			if (test) fclose(Fich_test);
			return;
		}
		Enabled = false;
		while (rc == LIBUSB_SUCCESS)
		{
			Application::DoEvents();
			rc = libusb_handle_events(NULL);
			if (transfert_fini) break;
		}
		// fin des t�ches de fond		 
		libusb_free_transfer(transfert);
		delete buffers;
		if (test) fclose(Fich_test);
		Enabled = true;
		Rec_Init = true;
	}
	private: System::Void button_Filtre_Click(System::Object^  sender, System::EventArgs^  e)
	{
		// transfert les coefficients du filtre dans le micro-controleur qui les charge dans le sigma-delta
		double coefficients[N_FILTRE] =   // extraits de Matlab
		{
			 0.183920201699362,     0.0733851728230403,   -0.0680015386790693,   -0.145894347034932,
			-0.123668250482790,    -0.0410296764320929,    0.0305284002161065,    0.0491981351634960,
			 0.0269319148595750,    0.00330880479737157,   0.00286726563446845,   0.0174885105375115,
			 0.0237846900264265,    0.0108592276809610,   -0.0105381197256412,   -0.0222717014586020,
			-0.0175760009732154,   -0.00504764462947583,   0.00282618095885551,   0.00204558620320313,
			-0.00177499154982921,  -0.00184570721638485,   0.00247807241434246,   0.00647327800115424,
			 0.00613579022798493,   0.00216327954424182,  -0.00165287862701378,  -0.00266790770927718,
			-0.00143479527467731,  -0.000170481761418747, -0.000140985730009316, -0.000811076417273096,
			-0.00102932635907949,  -0.000434121545567748,  0.000385359707988540,  0.000737707455865356,
			 0.000522042413448806,  0.000133025163653105, -6.53373333990531e-05, -4.09693530571867e-05,
			 3.03671203989688e-05,  2.65399917417235e-05, -2.93821463294089e-05, -6.18379854144075e-05,
			-4.58693641247505e-05, -1.21819211973428e-05,  6.64878321440797e-06,  9.78166781279591e-06
		};
		long int coeff_norm[N_FILTRE + 1]; //la derni�re valeur pour la checksum
		int i, nb_ecrit = 0, nb = (N_FILTRE + 1) * 4;
		unsigned char *p, q;
		if (!init_USB)
		{
			call_verb("Pas de liaison USB !\n", 1);
			return;
		}

		for (i = 0; i < N_FILTRE; i++) coeff_norm[i] = ((long int)floor(coefficients[i] * NORM_FILTRE) & 0x07fffff);
		coeff_norm[N_FILTRE] = 0;
		p = (unsigned char *)(&coeff_norm[0]);
		for (i = 0; i < N_FILTRE * 4; i++)
		{
			q = *p++;
			coeff_norm[N_FILTRE] += (long int)q;
		}

		write_command(handle, C_FILTRE, buf, 0);		//transfert des coefficients
/*		r = libusb_bulk_transfer(handle,_ADDR_ECR,p,nb,&nb_ecrit,TimeOut);
		if (r || (nb_ecrit!=nb))
			call_verb(String::Format("Erreur transfert des coefficients du filtre     retour: {0:G}   nb_�crit : \n", r,nb_ecrit),0);
		else
			call_verb("Transfert des coefficient du filtre \n",0);
*/


	}
	private: System::Void button_Reset_Altera_Click(System::Object^  sender, System::EventArgs^  e)
	{
		int ret;
		if (!init_USB)
		{
			call_verb("Pas de liaison USB !\n", 1);
			return;
		}
		ret = write_command(handle, C_RESET_ALTERA, buf, 0); // teste une commande
		if (test) call_verb("Reset de l'Altera \n", 0);
		Emis_Init = false;
		Rec_Init = false;
	}
	private: System::Void numericUpDown_Echantillons_ValueChanged(System::Object^  sender, System::EventArgs^  e)
	{
		float duree;

		duree = Decimal::ToDouble(numericUpDown_Echantillons->Value) * 1024 / f_ech;
		label_Duree->Text = String::Format("Dur�ee : {0:F1} ms", duree);
		Rec_Init = false;
	}
	private: System::Void button_Emission_Click(System::Object^  sender, System::EventArgs^  e)
	{	//pasage de la bande, du tps mort et de la dur�e
		int ret,nb_ecrit;
		unsigned int d_emis, d_bande, d_tps_mort;
		if (!init_USB)
		{
			call_verb("Pas de liaison USB !\n", 1);
			return;
		}
		if (!PLL_Init) numericUpDown_PLL_ValueChanged(this, e);
		if (test) call_verb("Emission \n", 0);
		bande = Decimal::ToDouble(numericUpDown_Bande->Value);
		duree_emis = Decimal::ToDouble(numericUpDown_Emis->Value) / f_ech * 4;
		duree_tps_mort = Decimal::ToDouble(numericUpDown_Tps_mort->Value) / f_ech * 4;

		d_bande = (unsigned int) floor(Decimal::ToDouble(numericUpDown_Bande->Value)*10+0.1);	// en hHz
		d_tps_mort = (unsigned int) Decimal::ToDouble(numericUpDown_Tps_mort->Value);		// en nb de p�riodes de freq centrale
		d_emis = (unsigned int) Decimal::ToDouble(numericUpDown_Emis->Value);				// en nb de p�riodes de freq centrale
		buf[0] = (d_bande & 0xFF00) >> 8;
		buf[1] = d_bande & 0xFF;
		buf[2] = (d_tps_mort & 0xFF00) >> 8;
		buf[3] = d_tps_mort & 0xFF;
		buf[4] = (d_emis & 0xFF00) >> 8;
		buf[5] = d_emis & 0xFF;
		ret = write_command(handle, C_EMISSION, buf, 0);
		ret = libusb_bulk_transfer(handle, _ADDR_ECR, &(buf[0]), 6, &nb_ecrit, TimeOut); //envoi des param�tres
		call_verb(String::Format("buf[0] = {0:G}, buf[1] = {1:G}\n",buf[0],buf[1]), 0);
		Emis_Init = true;
	}
	private: System::Void numericUpDown_PLL_ValueChanged(System::Object^  sender, System::EventArgs^  e)
	{
		int ret, c, C0 = 0, M = 0, nb_ecrit = 0, N = 0, im, in, in0;
		double freq, delta0, delta, A = 0.00256;

		freq = Decimal::ToDouble(numericUpDown_PLL->Value);
		f_ech = freq * RF;
		delta0 = 100;
		for (im = 1; im < 256; im++)
		{
			in0 = (int)(floor(((float)im) / 24)) + 1;
			for (in = in0; in < 255; in++)
			{
				c = (int) floor(0.49+((float)im) / ((float)in) / A / freq);
				if (c == 0) c = 1;
				delta = abs(freq - ((float)im) / ((float)in) / ((float)c) / A);
				if (delta < delta0)
				{
					delta0 = delta;
					M = im;
					N = in;
					C0 = c;
				}
			}
		}
		buf[0] = M % 256;
		buf[1] = N % 256;
		buf[2] = C0 % 256;
		buf[3] = C0 / 256;
		freq = ((float)M) / ((float)N) / ((float)C0) / A;
		if (test) call_verb(String::Format("M = {0:G}, N = {1:G}, C0 = {2:G}, Fheter = {3:F2}, Fclock = {4:F2} MHz\n", M, N, C0, freq, f_ech*0.032), 0);
		numericUpDown_Echantillons_ValueChanged(this, e);
		ret = write_command(handle, C_PLL, buf, 0);
		ret = libusb_bulk_transfer(handle, _ADDR_ECR, &(buf[0]), 4, &nb_ecrit, TimeOut); //envoi des param�tres
		if (nb_ecrit != 4) call_verb("Erreur dans le passage de param�tres\n", 0);
		PLL_Init = true;
		numericUpDown_Tps_mort_ValueChanged(this, e);
		numericUpDown_Emis_ValueChanged(this, e);
		Rec_Init = false;
	}
	private: System::Void listBox_NT_SelectedIndexChanged(System::Object^  sender, System::EventArgs^  e)
	{
		Rec_Init = false;
	}
	private: System::Void button_Em_Rec_Click(System::Object^  sender, System::EventArgs^  e) 
	{
		int r, nb_ecrit, rc = LIBUSB_SUCCESS, TAILLE;
		unsigned long int i,j, k;
		long t1, t2, periode;
		char commentaire[512]="Donn�es compl�mentaires du fichier .dat";
		float donnees[32];

		if (!init_USB)
		{
			call_verb("Pas de liaison USB !\n", 1);
			return;
		}
		if (!Emis_Init) button_Emission_Click(this, e);
		if (!Rec_Init) button_Recep_Click(this, e);
		if (!Fich_open) button_Fichier_Click(this, e);
		if (!Fich_open)
		{
			call_verb("Pas de fichier ouvert ! \n", 1);
			return;
		}
		Stop = false;
		button_Stop->Show();
		TAILLE = (int)(((long)nb_echant) * 8 / RF / NT); //Attention max : 0x60000 octets
		buffers = new unsigned char[TAILLE];
		callback = (libusb_transfer_cb_fn)fn_callback;
		transfert = libusb_alloc_transfer(0);
		libusb_fill_bulk_transfer(transfert, handle, _ADDR_LECT, buffers, TAILLE, callback, NULL, TimeOut);
		nb_tirs = Decimal::ToInt16(numericUpDown_Nb_Tirs->Value);
		Enable(false);
		periode = Decimal::ToUInt32(numericUpDown_Periode->Value);
		num_tir = 0;
		t1 = GetTickCount();
		if (nb_tirs)
			for (num_tir = 0; num_tir < nb_tirs; num_tir++)
			{
				transfert_fini = false;
				ligne_a_afficher = false;
				r = write_command(handle, C_EM_REC, buf, 0);	//envoi de la commande
				retour = libusb_submit_transfer(transfert);		// lancement de la t�che de fond
				t2 = GetTickCount();
				if (retour)
				{
					call_verb(String::Format("Tir n�{0:G} - Erreur lancement transfert \n", num_tir), 0);
					break;
				}
				else if (test) call_verb(String::Format("Tir n�{0:G}     {1:F3} s - ", num_tir, (GetTickCount() - t1) / 1000.0), 0);
				while (rc == LIBUSB_SUCCESS)
				{
					Application::DoEvents();
					rc = libusb_handle_events(NULL);
					if (transfert_fini) break;
				}
				while ((GetTickCount() - t1) < periode*(num_tir + 1)) 
				{
					if(ligne_a_afficher) affiche_ligne();
				}
				Application::DoEvents();
				if (Stop) break;
			}
		else
			while (!Stop)
			{
				transfert_fini = false;
				r = write_command(handle, C_EM_REC, buf, 0);	//envoi de la commande
				retour = libusb_submit_transfer(transfert);		// lancement de la t�che de fond
				t2 = GetTickCount();
				if (retour)
				{
					call_verb(String::Format("Tir n�{0:G} - Erreur lancement transfert \n", num_tir), 0);
					break;
				}
				else if (test) 	call_verb(String::Format("Tir n�{0:G}     {1:F3} s - ", num_tir, (GetTickCount() - t1) / 1000.0), 0);
				while (rc == LIBUSB_SUCCESS)
				{
					Application::DoEvents();
					rc = libusb_handle_events(NULL);
					if (transfert_fini) break;
				}
				while ((GetTickCount() - t1) < periode*num_tir)
				{
					if (ligne_a_afficher) affiche_ligne();
				}
				num_tir++;
				Application::DoEvents();
			}
		// fin de la t�che de fond		 
		libusb_free_transfer(transfert);
		delete buffers;
		// Ecriture du fichier log
		fwrite(commentaire, 512, 1, Fich_log);
		donnees[0] = (float)(f_ech / RF);
		donnees[1] = (float)(bande);
		donnees[2] = (float)(Decimal::ToInt16(numericUpDown_Emis->Value));
		donnees[3] = (float)(duree_emis);
		donnees[4] = (float)(Decimal::ToInt16(numericUpDown_Tps_mort->Value));
		donnees[5] = (float)(duree_tps_mort);
		donnees[6] = (float)(Decimal::ToDouble(numericUpDown_Echantillons->Value) * 1024);
		donnees[7] = (float)(Decimal::ToDouble(numericUpDown_Echantillons->Value) * 1024 / f_ech);
		donnees[8] = (float)(NT);
		if (nb_tirs) donnees[9] = (float)(nb_tirs);
		else donnees[9] = num_tir;
		donnees[10] = (float)(periode);
		fwrite(donnees, sizeof(float), 32, Fich_log);
		fclose(Fich_log);
		fclose(Fich);
		Fich_open = false;
		Enable(true);
		button_Stop->Hide();
		}
	private: System::Void numericUpDown_Emis_ValueChanged(System::Object^  sender, System::EventArgs^  e) 
	{
		float duree;

		duree = Decimal::ToDouble(numericUpDown_Emis->Value) / f_ech * 4;
		label_Emis->Text = String::Format("Dur�ee : {0:F2} ms", duree);
		Emis_Init = false;
	}
	private: System::Void numericUpDown_Tps_mort_ValueChanged(System::Object^  sender, System::EventArgs^  e) 
	{
		float duree;

		duree = Decimal::ToDouble(numericUpDown_Tps_mort->Value) / f_ech * 4;
		label_Tps_mort->Text = String::Format("Dur�ee : {0:F2} ms", duree);
		Emis_Init = false;
	}
	private: System::Void numericUpDown_Bande_ValueChanged(System::Object^  sender, System::EventArgs^  e) 
	{
		Emis_Init = false;
	}
	private: System::Void button_Fichier_Click(System::Object^  sender, System::EventArgs^  e) 
	{
		String ^name;
		String ^verbose;
		pin_ptr<const wchar_t> wch;
		size_t converted_Chars = 0, sizeInBytes;
		char *ch,ch1[1000];
		int nb_ecrit;

		if (Fich_open)
		{
			fclose(Fich);
			fclose(Fich_log);
		}
		Fich_open = false;
		if (saveFileDialog_Data->ShowDialog() != System::Windows::Forms::DialogResult::OK) //pas de choix de nom de fichier
			return;
		// un nom a �t� choisi
		name = saveFileDialog_Data->FileName;
		verbose = "Nom du fichier d'acquisition : " + name + "\n";
		call_verb(verbose, 0);
		wch = PtrToStringChars(name);
		sizeInBytes = ((name->Length + 1) * 2);
		ch = (char *)malloc(sizeInBytes);
		wcstombs_s(&converted_Chars, ch, sizeInBytes, wch, sizeInBytes);
		Fich = fopen(ch, "wb+");
		name = name->Remove(name->Length - 3);
		name = name->Insert(name->Length, "log");
		wch = PtrToStringChars(name);
		wcstombs_s(&converted_Chars, ch, sizeInBytes, wch, sizeInBytes);
		Fich_log = fopen(ch, "wb+");
		Fich_open = true;
	}
	private: System::Void button_Stop_Click(System::Object^  sender, System::EventArgs^  e) 
	{
		Stop = true;
	}
	private: System::Void button_Image_Click(System::Object^  sender, System::EventArgs^  e) 
	{
		Color couleur = ColorTranslator::FromOle(0x00);
		Imaging::BitmapData^ bmpData;
		Drawing::Rectangle rect = Drawing::Rectangle(0, 0, W_image, H_image * 2);
		Imaging::PixelFormat format = pictureBox_Image->Image->PixelFormat;
		for (long int i = 0;i < H_image*2; i++)
		{
			couleur = ColorTranslator::FromOle( (i%256) * 0x10101);
			for (long int j = 0; j < W_image; j++) Image_bitmap->SetPixel(j, i, couleur);
		}
		pictureBox_Image->Image = Image_bitmap;
		pictureBox_Image->Refresh();

		bmpData = Image_bitmap->LockBits(rect, Imaging::ImageLockMode::ReadWrite, format);
		char *p = (char *)bmpData->Scan0.ToPointer();
		memmove(data_image,p, H_image * 2 * W_image * 4);
		Image_bitmap->UnlockBits(bmpData);
	}
	private: System::Void vScrollBar_Image_Scroll(System::Object^  sender, System::Windows::Forms::ScrollEventArgs^  e) 
	{
		Bitmap^ bitmap1 = Image_bitmap;
		Imaging::PixelFormat format = pictureBox_Image->Image->PixelFormat;
		Drawing::Rectangle rect = System::Drawing::Rectangle(0, 0, W_image, H_image*2);
		Imaging::BitmapData^ bmpData = bitmap1->LockBits(rect, Imaging::ImageLockMode::ReadWrite, format);;
		char *p = (char *)bmpData->Scan0.ToPointer();
		premiere_ligne = vScrollBar_Image->Value;
		memmove(p, data_image + premiere_ligne * W_image * 4, H_image * W_image * 4);
		bitmap1->UnlockBits(bmpData);
		pictureBox_Image->Image = bitmap1;
		pictureBox_Image->Refresh();
	}
	private: System::Void button_Eff_Image_Click(System::Object^  sender, System::EventArgs^  e) 
	{
		Color couleur = ColorTranslator::FromOle(0);
		Imaging::BitmapData^ bmpData;
		Drawing::Rectangle rect = Drawing::Rectangle(0, 0, W_image, H_image * 2);
		Imaging::PixelFormat format = pictureBox_Image->Image->PixelFormat;

		for (int i = 0; i < H_image * 2; i++) for (int j = 0; j < W_image; j++) Image_bitmap->SetPixel(j, i, couleur);
		pictureBox_Image->Image = Image_bitmap;
		pictureBox_Image->Refresh();
		bmpData = Image_bitmap->LockBits(rect, Imaging::ImageLockMode::ReadWrite, format);
		char *p = (char *)bmpData->Scan0.ToPointer();
		memmove(data_image,p, 2*H_image * W_image * 4);
		Image_bitmap->UnlockBits(bmpData);
		num_ligne = 0;
		derniere_ligne = false;
	}
	private: System::Void checkBox_Test_CheckedChanged(System::Object^  sender, System::EventArgs^  e) 
	{
		test = checkBox_Test->Checked;
		groupBox_Test->Visible = test;
	}
	private: System::Void button_Config_Click(System::Object^  sender, System::EventArgs^  e) 
	{
		button_Initialisation_Click(this, e);
		numericUpDown_PLL_ValueChanged(this, e);
		Sleep(100);
		button_Emission_Click(this, e);
		Sleep(100);
		button_Recep_Click(this, e);
	}
	private: System::Void button_Initialisation_Click(System::Object^  sender, System::EventArgs^  e) 
	{
		button_Init_Click(this, e);
		if (handle == NULL) return; //Pas de liaison USB
		Sleep(100);
		button_Reset_Altera_Click(this, e);
		Sleep(100);
		button_InitSigma_Click(this, e);
		Sleep(100);
		init_fait = true;
	}
};
}