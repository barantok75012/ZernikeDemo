%% Demo Wavefront, PSF & Co.
%
% Created 11/01/2021 by Konogan

function PSFguiPrez

%% Init
close all
colordef black
% colordef white
U.N=128;    % image size
U.Z=45;     % Zernike poly
U.Z(2)=ceil((-3+sqrt(9+8*U.Z))/2); % Max deg of r
Coul=[jet(U.Z(2));.5 .5 .5];
VarList={
    'Lambda (nm)'
    'Zer Ø  (mm)'
    'Pup Ø  (%)'
    'Defoc  (mm)'
    'AL     (mm)'
    'PSFpix (µm)'
    };
Values=[
    450 650     % wavelenght  RGB=[565e-9 535e-9 430e-9]
    2   8       % pupil diameter
    0   100     % pourcentage
   -1   1       % Eye defocus
    21  24      % Eye lengh
    0.5 1.5     % Pixel size at PSF
    ];
fn=size(VarList,1);
VarList(end+(1:U.Z(1)))={'Z'};
Values(end+(1:U.Z(1)),1)=0:U.Z(1)-1;
fh=19*numel(VarList)+10;
U.fig(1)=figure(1);
set(U.fig(1),'Position',[20 60 330 fh],'Color','k')

% Add button
for kp=1:numel(VarList)
    
    if VarList{kp}=='Z'
        % Zernike line
        n=ceil((-3+sqrt(9+8*Values(kp,1)))/2);
        m=2*Values(kp,1) - n.*(n+2);
        VarList{kp}=num2str([n m],'Z(%g,%+g)');
        Values(kp,:)=0.5*[-1 1];
        U.Ctrl.Push(kp)=uicontrol('Style','pushbutton','String',VarList{kp},'HorizontalAlignment','Left',...
            'BackgroundColor',(1-0.4*(abs(m)+3)/(n+3))*Coul(n+1,:),'ForegroundColor',0.9*[1 1 1],...
            'Units','pixel','Position',[52 fh-19*kp 38 16],'UserData',[n m kp],...
            'Callback',@CalcPSF);
        VarList{kp}=num2str([n m],'Z_{%g}^{%g}');
    else
        % Parameter line
        n=size(Coul,1)-1;m=n-1;
        U.Ctrl.Push(kp)=uicontrol('Style','pushbutton','String',VarList{kp},'HorizontalAlignment','Left',...
            'BackgroundColor',(1-0.4*(abs(m)+3)/(n+3))*Coul(n+1,:),'ForegroundColor',0.9*[1 1 1],...
            'Units','pixel','Position',[2 fh-19*kp 88 16],'UserData',[n m kp],...
            'Callback',@CalcPSF);
    end
    % Left, Slider and Right
    U.Ctrl.Edit(kp,1)=uicontrol('Style','edit','String',Values(kp,1),'HorizontalAlignment','Left',...
        'BackgroundColor',(1-0.4*(abs(m)+3)/(n+3))*Coul(n+1,:),'ForegroundColor',0.9*[1 1 1],...
        'Units','pixel','Position',[sum(U.Ctrl.Push(kp).Position([1 3]))+2 fh-19*kp 40 16],...
        'Callback',@CalcPSF);
    U.Ctrl.Slider(kp)=uicontrol('Style','slider','Value',0.5,'HorizontalAlignment','Left',...
        'BackgroundColor',(1-0.4*(abs(m)+3)/(n+3))*Coul(n+1,:),'ForegroundColor',0.7*[1 1 1],...
        'Units','pixel','Position',[sum(U.Ctrl.Edit(kp,1).Position([1 3]))+2 fh-19*kp 150 16],...
        'Callback',@CalcPSF);
    U.Ctrl.Edit(kp,2)=uicontrol('Style','edit','String',Values(kp,2),'HorizontalAlignment','Left',...
        'BackgroundColor',(1-0.4*(abs(m)+3)/(n+3))*Coul(n+1,:),'ForegroundColor',0.9*[1 1 1],...
        'Units','pixel','Position',[sum(U.Ctrl.Slider(kp).Position([1 3]))+2 fh-19*kp U.Ctrl.Edit(kp,1).Position(3) 16],...
        'Callback',@CalcPSF);
    
end
U.Ctrl.Slider(3).Value=0.8;
n=size(Coul,1)-1;m=n+1;

% Refresh
U.Ctrl.Push(kp+1)=uicontrol('Style','pushbutton','String','Refresh','HorizontalAlignment','Center',...
    'BackgroundColor',(1-0.4*(abs(m)+3)/(n+3))*Coul(n+1,:),'ForegroundColor',0.9*[1 1 1],...
    'Units','pixel','Position',[2 fh-19*7 50 16],'UserData',[n m kp+1],...
    'Callback',@CalcPSF);
% Record in animated gif
U.Ctrl.Push(kp+2)=uicontrol('Style','pushbutton','String','Rec','HorizontalAlignment','Center',...
    'BackgroundColor',(1-0.4*(abs(m)+3)/(n+3))*Coul(n+1,:),'ForegroundColor',0.9*[1 1 1],...
    'Units','pixel','Position',[2 fh-19*8 50 16],'UserData',[n m kp+2],...
    'Callback',@CalcPSF);
% Reset sliders to 0
U.Ctrl.Push(kp+3)=uicontrol('Style','pushbutton','String','0','HorizontalAlignment','Center',...
    'BackgroundColor',(1-0.4*(abs(m)+3)/(n+3))*Coul(n+1,:),'ForegroundColor',0.9*[1 1 1],...
    'Units','pixel','Position',[2 fh-19*9 50 16],'UserData',[n m kp+3],...
    'Callback',@CalcPSF);
% Random sliders
U.Ctrl.Push(kp+4)=uicontrol('Style','pushbutton','String','?','HorizontalAlignment','Center',...
    'BackgroundColor',(1-0.4*(abs(m)+3)/(n+3))*Coul(n+1,:),'ForegroundColor',0.9*[1 1 1],...
    'Units','pixel','Position',[18 fh-19*kp 16 17*U.Z(1)-2],'UserData',[n m kp+4],...
    'Callback',@CalcPSF);
% Play sliders
U.Ctrl.Push(kp+5)=uicontrol('Style','pushbutton','String','>','HorizontalAlignment','Center',...
    'BackgroundColor',(1-0.4*(abs(m)+3)/(n+3))*Coul(n+1,:),'ForegroundColor',0.9*[1 1 1],...
    'Units','pixel','Position',[34 fh-19*kp 16 17*U.Z(1)-2],'UserData',[n m kp+5],...
    'Callback',@CalcPSF);
U.pos=0;
set(U.fig(1),'UserData',U)
% I had to add this line to refresh 'CurrentPoint' in fig 1, I don't know why ?
set(U.fig(1),'WindowButtonMotionFcn','set(gcf,''CurrentPoint'',get(gcf,''CurrentPoint''));')
CalcPSF(U.Ctrl.Push(kp+5))


    function CalcPSF(src,~)
        %% Refresh graph
        % disp(datetime('now'))
        U=get(src.Parent,'UserData');
        nf=1;   % number of frame (or loop) to display animation
        % Call-dependent initialization
        if strcmp(src.Style,'pushbutton')
            if src.UserData(2)<U.Z(2)
                % Button with a slider
                U.Ctrl.Slider(src.UserData(3)).Value=0.5;
            else
                % Button without slider
                c=get(U.fig(1),'CurrentPoint');
                c=1-(c(2)-src.Position(2))/src.Position(4);
                switch src.String
                    case '0'
                        % set Zernike coef to zero
                        for kz=1:U.Z(1)
                            U.Ctrl.Slider(kz+fn).Value=0.5;
                        end
                    case 'Rec'
                        if all(U.Ctrl.Push(end-3).BackgroundColor==[1 0 0])
                            set(U.fig(1),'Name','')
                            src.BackgroundColor=U.Ctrl.Push(1).BackgroundColor;
                        else
                            file=clock;
                            datestr(file);
                            file=['C:\Users\User\Downloads\fig ' datestr(file,29) ' ' datestr(file,15) 'm' num2str(file(6),'%06.3f') '.gif'];
                            file(end-13)='h';file(end-7)='s';
                            set(U.fig(1),'Name',file)
                            src.BackgroundColor='r';
                            disp(file)
                        end
                    case '?'
                        % set Zernike coef to random value
                        for kz=1:U.Z(1)
                            U.Ctrl.Slider(kz+fn).Value=c*(rand-0.5)/(0.5*U.Ctrl.Push(kz+fn).UserData(1)+1)+0.5;
                        end
                    case '>'
                        % set progressively Zernike coef to random value in animated loop
                        for kz=1:U.Z(1)
                            U.Ctrl.Slider(kz+fn).UserData=[U.Ctrl.Slider(kz+fn).Value,...
                                c*(rand-0.5)/(0.5*U.Ctrl.Push(kz+fn).UserData(1)+1)+0.5];
                        end
                        nf=10; % Number of frame (or loop in animation)
                end
            end
        end
        
        % Init optical parameters
        lambda  =1e-9*(str2double(U.Ctrl.Edit(1,2).String)*U.Ctrl.Slider(1).Value+str2double(U.Ctrl.Edit(1,1).String)*(1-U.Ctrl.Slider(1).Value));
        zerdiam =1e-3*(str2double(U.Ctrl.Edit(2,2).String)*U.Ctrl.Slider(2).Value+str2double(U.Ctrl.Edit(2,1).String)*(1-U.Ctrl.Slider(2).Value));
        pupnorm =1e-2*(str2double(U.Ctrl.Edit(3,2).String)*U.Ctrl.Slider(3).Value+str2double(U.Ctrl.Edit(3,1).String)*(1-U.Ctrl.Slider(3).Value));
        defocus =1e-3*(str2double(U.Ctrl.Edit(4,2).String)*U.Ctrl.Slider(4).Value+str2double(U.Ctrl.Edit(4,1).String)*(1-U.Ctrl.Slider(4).Value));
        axial   =1e-3*(str2double(U.Ctrl.Edit(5,2).String)*U.Ctrl.Slider(5).Value+str2double(U.Ctrl.Edit(5,1).String)*(1-U.Ctrl.Slider(5).Value));
        psfpix  =1e-6*(str2double(U.Ctrl.Edit(6,2).String)*U.Ctrl.Slider(6).Value+str2double(U.Ctrl.Edit(6,1).String)*(1-U.Ctrl.Slider(6).Value));
        no=1.336; % Eye index
        % [h w c]=size(ImA);
        N2=2.^ceil(log2(U.N));	% 2^n size for fast fft
        % Pixel size at pupil in mm=lambda * scrdst / scrsz;
        Xp=linspace(-.5,.5,N2) * lambda * axial / (no * psfpix);
        [Xp,Yp]=meshgrid(Xp);
        Rp=sqrt(Xp.^2 + Yp.^2);
        Rn=Rp/(zerdiam/2);      % Pupil normalized to aperture diameter
             
        %% Create wavefront
        % Zernike polynomial surface in lambda
        idr=Rn<=1;
        % r power pre-calculation
        r=Rn(idr);
        t=atan2(Yp(idr),Xp(idr));
        rpowers=0:U.Z(2)-1;
        rpowern = cumprod(r*ones(1,U.Z(2)-1),2);
        rpowern=[ones(size(r)) rpowern];
        % Polynomials
        for kf=1:nf
            W=zeros(size(Rn));
            Zcoef=zeros(U.Z(1),1);
            for kz=1:U.Z(1)
                n(kz)=ceil((-3+sqrt(1+8*kz))/2);m(kz)=2*(kz-1)-n(kz).*(n(kz)+2);
                % Radial part of Zernike (From Paul Fricker 11/13/2006)
                y=zeros(size(r));
                s=0:(n(kz)-abs(m(kz)))/2;
                pows=n(kz):-2:abs(m(kz));
                for kt=length(s):-1:1
                    p=(1-2*mod(s(kt),2))*prod(2:(n(kz)-s(kt)))/ ...
                        prod(2:s(kt))/prod(2:((n(kz)-abs(m(kz)))/2-s(kt)))/ ...
                        prod(2:((n(kz)+abs(m(kz)))/2-s(kt)));
                    idx=(pows(kt)==rpowers);
                    y=y+p*rpowern(:,idx);
                end
                % Normalization (if needed)
                y=y*sqrt((1+(m(kz)~=0))*(n(kz)+1));
                if m(kz)>0
                    y=y.*sin(t*m(kz)');
                elseif m(kz)<0
                    y=y.*cos(t*m(kz)');
                end
                % Add Zernike weight
                if nf>1 % Refresh slider position in case of animation
                    U.Ctrl.Slider(kz+fn).Value=U.Ctrl.Slider(kz+fn).UserData*[nf-kf;kf]/nf;
                end
                Zcoef(kz)=1e-6*(str2double(U.Ctrl.Edit(kz+fn,2).String)*U.Ctrl.Slider(kz+fn).Value+str2double(U.Ctrl.Edit(kz+fn,1).String)*(1-U.Ctrl.Slider(kz+fn).Value));
                W(idr)=W(idr)+Zcoef(kz)*y;
            end
            % Eye focusing
            foc=no*(1/axial-1/(axial+defocus))*(Xp.^2+Yp.^2);
            %% From pupil to retina and PSF
            E=exp(2*1i*pi*(W+foc)/lambda);  % Complex amplitude
            %SC effect
            % scex=0.4*oeil;    % lateral shift depending left or right eye
            % scey=+.20;        % vertical shift vs. pupil center in mm (Applegate -combined data- scey=+.20mm)
            % scerho=.05;       % intensity SCE attenuation coefficient in mm-2 (Applegate -combined data- scerho=0.05mm-2)
            E=E.*10.^(-.05*((1e3*Xp-0.4).^2+(1e3*Yp-0.2).^2)/2);
            E(Rn>pupnorm)=0;                % Set aperture size
            
            % Create point-spread function
            psf=abs(fftshift(fft2(ifftshift(E)))).^2;
            psf=psf/sum(psf(:));            % Normalize to unity energy
            disp(['Peak of PSF =' num2str(max(psf(:)))])
            xr=linspace(-.5,.5,N2)*N2*psfpix;
            
            %% Ray tracing

            K=2*W/(no-1) + abs(sqrt( ( (axial+defocus)*(no-1)/no )^2-Xp.^2-Yp.^2 ));
            
            %Nx=Nx(1:f:end,1:f:end);Ny=Ny(1:f:end,1:f:end);Nz=Nz(1:f:end,1:f:end);
            %Px=Xp(1:f:end,1:f:end);Py=Yp(1:f:end,1:f:end);Pz=K(1:f:end,1:f:end);
            
            % Ray list
            nr=60; % number of ray
            % Grid hexa
            [y x]=meshgrid(linspace(-1,1,2*ceil(sqrt(nr/pi))));
            x=[x;x+0.5*diff(x(1:2))]; %#ok<AGROW>
            y=sqrt(3)*[y;y+0.5*diff(y(1,1:2))];
            x=x(:);y=y(:);
            % Points close to center
            z=hypot(x,y);
            [z s]=sort(z);
            nr=find(z<1,1,'last');  % Real number of ray
            x=x(s(1:nr))*0.5*pupnorm*zerdiam/z(nr);
            y=y(s(1:nr))*0.5*pupnorm*zerdiam/z(nr);
            c=(axial+defocus)*(no-1)/no; % min(K(Rn<1));

            % Intersection onto cornea
            % z= sqrt( ((axial+defocus)*(no-1)/no )^2 - ( z(1:nr)*0.5*pupnorm*zerdiam/z(nr) ).^2); % W is neglected
            % z=z-c
            % Normal to cornea
            % [Nx,Ny,Nz]=surfnorm(Xp,Yp,K);
            % Nx=interp2(Xp,Yp,Nx,x,y,'spline');Ny=interp2(Xp,Yp,Ny,x,y,'spline');Nz=interp2(Xp,Yp,Nz,x,y,'spline');
            % Nx.^2+Ny.^2+Nz.^2-1
            % Refracted ray
            % p=(sqrt(1-(1-Nz.^2)/no^2)*[1 1 1]).*[Nx Ny Nz]+([-Nz.*Nx -Nz.*Ny 1-Nz.*Nz])/no;

            % Intersection onto wavefront
            z=sqrt((axial+defocus).^2-x.^2-y.^2)-(axial+defocus); % W is neglected
            % Normal to wavefront
            [Nx,Ny,Nz]=surfnorm(Xp,Yp,(+0.5*W/no+sqrt((axial+defocus).^2-Xp.^2-Yp.^2)));
            Nx=interp2(Xp,Yp,Nx,x,y,'spline');Ny=interp2(Xp,Yp,Ny,x,y,'spline');Nz=interp2(Xp,Yp,Nz,x,y,'spline');
            % Ray normal to wavefront
            p=[Nx Ny Nz];
            
            %% Display
            
            W(Rn>1)=NaN;
            K(Rn>1)=NaN;
            v=((-axial-z)*[1 1 1 1]+ones(nr,1)*[-1e-3 0 -defocus +1e-3])./(p(:,3)*[1 1 1 1]);            
            g=10;
            
            if ~isfield(U,'Ax')
                %% Init graph
                U.fig(2)=figure(2);set(U.fig(2),'Position',...
                    [U.fig(1).Position(1:2)+[U.fig(1).Position(3) 0] 1500 fh],'Color','k')
                U.Ax(1)=axes;set(U.Ax(1),'Position',[0.06 0.54 0.45 0.42])
                % Horizontal mode
                U.Gra(1)=surf(1e3*Xp,1e3*Yp,1e6*W,'Clipping','off');
                title('Wavefront');xlabel(sprintf('mm'));zlabel(sprintf('\\mum'));
                axis tight equal;rotate3d on;zlim([-1 1]);
                % Vertical mode
                % U.Gra(1)=surf(1e6*W,1e3*Xp,1e3*Yp,'Clipping','off');
                % title('Wavefront');zlabel(sprintf('mm'));xlabel(sprintf('\\mum'));
                % axis tight equal;rotate3d on;xlim([-1 1]);
                
                U.Ax(2)=axes;set(U.Ax(2),'Position',[0.55 0.54 0.45 0.42])
                U.Gra(2)=surf(1e6*xr,1e6*xr,psf,'EdgeColor','none');
                title('PSF');xlabel(sprintf('\\mum'));
                axis tight equal;view(0,90)
                
                U.Ax(3)=axes;set(U.Ax(3),'Position',[0.06 0.05 0.45 0.45])
                hold on
                % figure(2);hold on
                U.Gra(3)=surf(1e3*Yp,1e3*(K-c),1e3*Xp);
                U.Ray=plot3(1e3*[y y y+v(:,1).*p(:,2)]',1e3*[1e-3*ones(nr,1) z z+v(:,1).*p(:,3)]',...
                    1e3*[x x x+v(:,1).*p(:,1)]','.-');
                title('Ray tracing');
                axis tight equal;view(-125,10);grid on

                U.Ax(4)=axes;set(U.Ax(4),'Position',[0.55 0.05 0.45 0.45])
                hold on
                % figure(2);hold on
                U.Ray(:,2)=plot3(1e3*[y y y+v(:,1).*p(:,2)]',1e3*[1e-3*ones(nr,1) z z+v(:,1).*p(:,3)]',...
                    1e3*[x x x+v(:,1).*p(:,1)]','.-');
                title('Zoom');
                axis tight equal;view(-125,10);grid on
                
                Coul=flipud(cool(20)*diag([1 1 0]));
                Coul=Coul(1+floor(19*hypot(x,y)/(0.5*pupnorm*zerdiam)),:);
                for kz=1:nr
                    U.Ray(kz,1).Color=Coul(kz,:);
                    U.Ray(kz,2).Color=Coul(kz,:);
                end
                for kz=[1 3]
                    U.Gra(kz).FaceAlpha='flat';U.Gra(kz).FaceColor='flat';
                    U.Gra(kz).EdgeColor='interp';U.Gra(kz).AlphaDataMapping = 'none';
                    U.Gra(kz).CData=1e6*W;
                end
                % linkprop(U.Ax(1:2),{'CameraPosition','CameraUpVector'});
                % linkprop(U.Ax(3:4),{'CameraPosition','CameraUpVector'});
                
                set(src.Parent,'UserData',U)
            else
                %% Refresh graph
                % Wavefront
                U.Gra(1).XData=1e3*Xp; U.Gra(1).YData=1e3*Yp; U.Gra(1).ZData=1e6*W;U.Gra(1).CData=1e6*W;
                U.Ax(1).Title.String=num2str([std(1e6*W(:),'omitnan') 1e9*lambda 1e3*pupnorm*zerdiam],'Wavefront (rms=%05.3f \\lambda=%5.1f PØ=%04.2f)');
                
                % PSF
                U.Gra(2).XData=1e6*xr;   U.Gra(2).YData=1e6*xr; U.Gra(2).ZData=1e6*psf*xr(end)/max(psf(:));%  U.Gra(2).CData=psf;
                U.Ax(2).Title.String=num2str(1e3*[defocus axial],'PSF (defoc=%05.2f AL=%05.2f)');
                
                U.Gra(3).XData=1e3*Yp; U.Gra(3).YData=1e3*(K-c); U.Gra(3).ZData=1e3*Xp;
                for kz=1:nr
                    U.Ray(kz,1).XData=1e3*[y(kz) y(kz) y(kz)+v(kz,1)*p(kz,2)];
                    U.Ray(kz,1).YData=1e3*[1e-3  z(kz) z(kz)+v(kz,1)*p(kz,3)];
                    U.Ray(kz,1).ZData=1e3*[x(kz) x(kz) x(kz)+v(kz,1)*p(kz,1)];
                    U.Ray(kz,2).XData=1e3*(y(kz)+v(kz,:)*p(kz,2))*g;
                    U.Ray(kz,2).YData=1e3*(z(kz)+v(kz,:)*p(kz,3));
                    U.Ray(kz,2).ZData=1e3*(x(kz)+v(kz,:)*p(kz,1))*g;
                    %if abs(y(kz)) > 5e-4  % To keep only ray in vertical plan
                    %    U.Ray(kz,2).YData = NaN*[1 1 1 1];
                    %end
                end
            end
            
            % For simplified graph (no PSF)
            % U.Gra(1).YData=1e3*Xp; U.Gra(1).ZData=1e3*Yp; U.Gra(1).XData=1e6*W;
            % U.Ax(2).Visible = 'off';
            % U.Gra(2).Visible = 'off';
            % U.Ax(4).Position = U.Ax(2).Position;
            % U.Ax(4).CameraPosition = [-13.0133 -22.5000 0];
            % U.Ax(4).YLim = [-23 -22];U.Ax(4).ZLim = 0.3*[-1 1];
            % U.Ax(3).Position(3) = 0.90;
            
            U.Gra(3).CData=U.Gra(1).CData;U.Gra(1).AlphaData=0.8-(Rn>pupnorm);U.Gra(3).AlphaData=0.7-(Rn>pupnorm);
            drawnow
            file=get(U.fig(1),'Name');
            if numel(file)
                figure(U.fig(2))
                frame=getframe(U.fig(2));
                [RGB,badmap]=frame2im(frame); %#ok<ASGLU>
                [IND,map]=rgb2ind(RGB,256,'dither');
                trs=round(mode(double([IND(1,:) IND(end,:) IND(:,1)' IND(:,end)'])));
                % trs=-1; % pb of transparency with black background
                if exist(file,'file')
                    imwrite(IND,map,file,'gif','DelayTime',0.1,'DisposalMethod','restoreBG',...
                        'TransparentColor',trs,'WriteMode','append');
                else
                    imwrite(IND,map,file,'gif','DelayTime',1,'DisposalMethod','restoreBG',...
                        'TransparentColor',trs,'WriteMode','overwrite','LoopCount',1000);
                end
            end
        end
        %% Check FFT parameters
        if max(Rn(:))<sqrt(2)
            warning('Sampling is not sufficient to reconstruct the entire wavefront.')
            warning('  Reduce Zer Ø or PSF pixel size.')
            U.Ctrl.Push(2).BackgroundColor=[1 0 0];U.Ctrl.Slider(2).BackgroundColor=[1 0 0];
            U.Ctrl.Push(6).BackgroundColor=[1 0 0];U.Ctrl.Slider(6).BackgroundColor=[1 0 0];
            U.Ax(1).YLabel.String='Reduce pupil or PSF pixel size';
            U.Ax(1).YColor=[1 0 0];U.Ax(1).XColor=[1 0 0];
        else
            s=U.Ctrl.Push(1).BackgroundColor;
            U.Ctrl.Push(2).BackgroundColor=s;U.Ctrl.Slider(2).BackgroundColor=s;
            U.Ctrl.Push(6).BackgroundColor=s;U.Ctrl.Slider(6).BackgroundColor=s;
            U.Ax(1).YLabel.String='';
            U.Ax(1).YColor=U.Ax(2).YColor;U.Ax(1).XColor=U.Ax(2).YColor;
        end
        
    end
end
